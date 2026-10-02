"""Bounded OpenAI-compatible V2 adapters with one explicit provider factory."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import time
from dataclasses import asdict, dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx

from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.evidence_validation import EvidenceRegistry, validate_analysis
from backend.services.synchronization import finite

TELEMETRY_ALLOWLIST = frozenset({"time_s", "speed", "brake", "acceleration", "jerk", "mode"})


def filtered_telemetry(rows: tuple[dict, ...]) -> list[dict]:
    result = []
    previous = None
    for row in rows:
        values = {key: value for key, value in row.items() if key in TELEMETRY_ALLOWLIST}
        if "time_s" not in values or not finite(values["time_s"]) or values["time_s"] < 0:
            raise ValueError("telemetry requires finite video-second timestamps")
        if previous is not None and values["time_s"] <= previous:
            raise ValueError("telemetry must be ordered")
        previous = values["time_s"]
        for key, value in values.items():
            if key == "mode":
                if value not in {"AUTO", "MANUAL", "UNKNOWN"}:
                    raise ValueError("mode must be an approved non-identifying enum")
            elif not finite(value):
                raise ValueError("allowed telemetry signals must be finite numeric values")
        result.append(values)
    return result


@dataclass(frozen=True)
class AnalysisContext:
    registry: EvidenceRegistry
    duration_s: float
    frames: tuple[EvidenceAsset, ...]
    telemetry_rows: tuple[dict, ...] = ()


@dataclass(frozen=True)
class ProviderConfig:
    kind: str
    endpoint: str
    model: str
    revision: str
    allowed_hosts: tuple[str, ...] = ()
    egress_approved: bool = False
    timeout_s: float = 30.0
    max_attempts: int = 2
    max_frames: int = 32
    max_image_bytes: int = 20 * 1024 * 1024
    max_telemetry_rows: int = 1000
    max_output_bytes: int = 1024 * 1024
    max_output_tokens: int = 4096
    prompt_version: str = "evidence-v2-1"
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None
    pricing_source: str | None = None


@dataclass(frozen=True)
class ProviderResult:
    analysis: AIIncidentAnalysisV2
    provenance: dict
    usage: dict


class VLMProvider(Protocol):
    def analyze(self, context: AnalysisContext) -> ProviderResult: ...


class HTTPVLMProvider:
    def __init__(self, config: ProviderConfig, *, client: httpx.Client | None = None, api_key: str | None = None):
        self.config, self.client, self.api_key = config, client, api_key

    def analyze(self, context: AnalysisContext) -> ProviderResult:
        config = self.config
        if not finite(context.duration_s) or context.duration_s <= 0 or not 0 < len(context.frames) <= config.max_frames or len(context.telemetry_rows) > config.max_telemetry_rows:
            raise ValueError("context exceeds frame/telemetry budget or invalid duration")
        timestamps = [frame.time_start_s for frame in context.frames]
        if timestamps != sorted(set(timestamps)) or any(not finite(t) or not 0 <= t < context.duration_s for t in timestamps):
            raise ValueError("frames must be unique and ordered in video seconds")
        refs = {asset.evidence_id: asset for asset in context.registry.assets}
        images = []
        byte_count = 0
        for frame in context.frames:
            if refs.get(frame.evidence_id) != frame or (frame.recording_id, frame.candidate_id) != (context.registry.recording_id, context.registry.candidate_id):
                raise ValueError("frame must belong to scoped evidence registry")
            if config.kind == "external_api" and (frame.privacy_state, frame.privacy_validation) != ("MASKED", "PASSED"):
                raise ValueError("privacy validation must pass before external egress")
            if not frame.path.is_file() or file_hash(frame.path) != frame.sha256 or frame.media_type != "image/jpeg":
                raise ValueError("frame hash/type invalid")
            byte_count += frame.path.stat().st_size
            if byte_count > config.max_image_bytes:
                raise ValueError("frame byte budget exceeded")
            images.append({"type": "text", "text": f"{frame.evidence_id} at video_seconds={frame.time_start_s}"})
            images.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(frame.path.read_bytes()).decode("ascii")}})
        telemetry = filtered_telemetry(context.telemetry_rows)
        refs_payload = [{"evidence_id": item.evidence_id, "source": item.source, "start_s": item.time_start_s, "end_s": item.time_end_s} for item in context.registry.assets]
        prompt = "Analyze only supplied chronological evidence. Cite valid evidence IDs/time/source. Distinguish OBSERVED, SUPPORTED_INFERENCE, HYPOTHESIS, UNKNOWN. Internal causes without logs must remain UNKNOWN/HYPOTHESIS. Conflicts and missing coverage go in unknowns. Return only schema 2.0 JSON with DRAFT; never approve. " + json.dumps({"duration_s": context.duration_s, "telemetry": telemetry, "evidence": refs_payload})
        payload = {"model": config.model, "temperature": 0, "max_tokens": config.max_output_tokens, "response_format": {"type": "json_schema", "json_schema": {"name": "incident_analysis_v2", "strict": True, "schema": AIIncidentAnalysisV2.model_json_schema()}}, "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, *images]}]}
        headers = {"Authorization": "Bearer " + self.api_key} if self.api_key else {}
        owned_client = self.client is None
        client = self.client or httpx.Client(trust_env=False)
        start = time.monotonic()
        try:
            for attempt in range(1, config.max_attempts + 1):
                try:
                    with client.stream("POST", config.endpoint, json=payload, headers=headers, timeout=config.timeout_s, follow_redirects=False) as response:
                        if response.status_code in {429, 500, 502, 503, 504}:
                            if attempt == config.max_attempts:
                                raise ValueError("provider unavailable after bounded attempts")
                            continue
                        if response.status_code != 200:
                            raise ValueError("provider rejected request; no automatic retry")
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > config.max_output_bytes:
                                raise ValueError("provider response exceeded budget")
                    decoded = json.loads(content)
                    raw = decoded["choices"][0]["message"]["content"]
                    analysis = AIIncidentAnalysisV2.model_validate_json(raw, context={"video_duration_s": context.duration_s})
                    validate_analysis(analysis, context.registry, context.duration_s)
                    usage = decoded.get("usage", {})
                    input_tokens, output_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
                    if any(value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0) for value in (input_tokens, output_tokens)):
                        raise ValueError("provider usage must be nonnegative integers")
                    cost = None
                    if attempt == 1 and input_tokens is not None and output_tokens is not None and config.input_usd_per_million is not None and config.output_usd_per_million is not None:
                        cost = (input_tokens * config.input_usd_per_million + output_tokens * config.output_usd_per_million) / 1_000_000
                    provenance = {"provider": config.kind, "model": config.model, "revision": config.revision, "prompt_version": config.prompt_version, "schema_version": "2.0", "config_hash": hashlib.sha256(json.dumps(asdict(config), sort_keys=True).encode()).hexdigest(), "input_hashes": [frame.sha256 for frame in context.frames], "pricing_source": config.pricing_source}
                    return ProviderResult(analysis, provenance, {"input_tokens": input_tokens, "output_tokens": output_tokens, "attempts": attempt, "latency_s": time.monotonic() - start, "cost_usd": cost, "retry_cost": "NOT_MEASURED" if attempt > 1 else "NO_RETRY"})
                except httpx.TransportError as exc:
                    if attempt == config.max_attempts:
                        raise ValueError("provider unavailable after bounded attempts") from exc
                except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                    raise ValueError("provider returned an invalid response/schema") from exc
        finally:
            if owned_client:
                client.close()
        raise ValueError("provider unavailable")


class ExternalVLMProvider(HTTPVLMProvider):
    """External API profile; all frames require privacy validation."""


class SelfHostedVLMProvider(HTTPVLMProvider):
    """Internal OpenAI-compatible profile; real GPU throughput NOT_MEASURED."""


def create_provider(config: ProviderConfig, *, client: httpx.Client | None = None, api_key: str | None = None) -> VLMProvider:
    if not config.model.strip() or not config.revision.strip() or not finite(config.timeout_s) or not 0 < config.timeout_s <= 120:
        raise ValueError("model/revision and bounded timeout required")
    for value, ceiling in ((config.max_attempts, 3), (config.max_frames, 256), (config.max_image_bytes, 100 * 1024 * 1024), (config.max_telemetry_rows, 10000), (config.max_output_bytes, 10 * 1024 * 1024), (config.max_output_tokens, 32768)):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= ceiling:
            raise ValueError("provider budgets must be finite positive integers")
    for price in (config.input_usd_per_million, config.output_usd_per_million):
        if price is not None and (not finite(price) or price < 0 or not config.pricing_source):
            raise ValueError("pricing requires finite rates and dated source")
    endpoint = urlparse(config.endpoint)
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or not endpoint.hostname:
        raise ValueError("endpoint must not contain credentials/query/fragment")
    if config.kind == "external_api":
        if not config.egress_approved or endpoint.scheme != "https" or endpoint.hostname not in config.allowed_hosts:
            raise ValueError("external endpoint requires HTTPS allowlist and explicit egress policy")
        return ExternalVLMProvider(config, client=client, api_key=api_key)
    if config.kind == "self_hosted":
        try:
            address = ipaddress.ip_address(endpoint.hostname)
            internal = address.is_private or address.is_loopback
        except ValueError:
            internal = endpoint.hostname == "localhost"
        if not internal or endpoint.scheme not in {"http", "https"}:
            raise ValueError("self-hosted endpoint must be internal literal IP or localhost")
        return SelfHostedVLMProvider(config, client=client, api_key=api_key)
    raise ValueError("unsupported provider profile")
