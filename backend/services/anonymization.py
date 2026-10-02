"""Frame masking with an explicit detector and independent review gate.

No production detector is selected here. Motion video remains blocked until a
full-frame temporal detector/validator is integrated and benchmarked.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.video import VideoService


@dataclass(frozen=True)
class MaskRegion:
    x: int
    y: int
    width: int
    height: int
    kind: str


@dataclass(frozen=True)
class PrivacyPolicy:
    detector_version: str
    reviewer: str


@dataclass(frozen=True)
class PrivacyResult:
    asset: EvidenceAsset
    detector_version: str
    reviewer: str
    regions: tuple[MaskRegion, ...]
    source_sha256: str


def mask_and_validate(asset: EvidenceAsset, policy: PrivacyPolicy, *, detector: Callable[[Path], list[MaskRegion]], review: Callable[[Path, list[MaskRegion]], bool], output_root: Path, service: VideoService | None = None) -> PrivacyResult:
    if asset.media_type != "image/jpeg":
        raise ValueError("video privacy requires a full motion detector/validator; frame masks cannot approve a clip")
    if not policy.detector_version.strip() or not policy.reviewer.strip():
        raise ValueError("privacy detector version and independent reviewer required")
    service = service or VideoService()
    try:
        if file_hash(asset.path) != asset.sha256:
            raise ValueError("source hash changed")
        found = detector(asset.path)
        if not isinstance(found, list) or any(not isinstance(region, MaskRegion) for region in found):
            raise ValueError("invalid detector output")
        probe = subprocess.run([service.ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(asset.path)], capture_output=True, text=True, check=True, timeout=30)
        dimensions = json.loads(probe.stdout)["streams"][0]
        for region in found:
            if region.kind not in {"FACE", "PLATE"} or any(isinstance(value, bool) or not isinstance(value, int) for value in (region.x, region.y, region.width, region.height)) or min(region.x, region.y) < 0 or min(region.width, region.height) <= 0 or region.x + region.width > dimensions["width"] or region.y + region.height > dimensions["height"]:
                raise ValueError("detector region outside frame")
        fingerprint = json.dumps([asset.sha256, asdict(policy), [asdict(region) for region in found]], sort_keys=True)
        directory = Path(output_root) / hashlib.sha256(fingerprint.encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "masked.jpg"
        if target.resolve() == asset.path.resolve():
            raise ValueError("mask output must not overwrite source")
        filters = ",".join(f"drawbox=x={region.x}:y={region.y}:w={region.width}:h={region.height}:color=black:t=fill" for region in found) or "null"
        service._run_ffmpeg(["-y", "-i", str(asset.path), "-vf", filters, "-frames:v", "1", str(target)])
        if review(target, found) is not True:
            raise ValueError("masked frame was not approved by review")
        masked = replace(asset, path=target, sha256=file_hash(target), privacy_state="MASKED", privacy_validation="PASSED")
        result = PrivacyResult(masked, policy.detector_version, policy.reviewer, tuple(found), asset.sha256)
        service.write_json(directory / "privacy.json", asdict(result))
        return result
    except Exception as exc:
        raise ValueError("privacy masking/validation failed; egress and playback blocked") from exc
