"""Observe each image independently, then decide once from ordered observations."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.services.evidence_extraction import file_hash
from backend.services.evidence_validation import validate_analysis
from backend.services.prompt_io import append_output, read_prompt
from backend.services.qwen_local import LocalQwenProvider, ensure_ollama_runtime
from backend.services.vlm_provider import (
    ProviderResult,
    batch_registry,
    detection_output_schema,
    filtered_telemetry,
    sample_telemetry,
)


class FrameObservation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    description: str = Field(min_length=1, max_length=1500)
    pedestrians_visible: bool
    pedestrian_positions: list[str] = Field(max_length=20)
    other_objects: list[str] = Field(max_length=20)
    contact_evidence: Literal['VISIBLE_CONTACT', 'NO_VISIBLE_CONTACT', 'UNKNOWN']
    occlusions: list[str] = Field(max_length=20)


OBSERVE_PROMPT = (
    'Describe ONLY visible evidence in this ONE road-scene image, in Vietnamese. '
    'Identify pedestrians, their positions relative to the roadway and ego vehicle, '
    'visible pose, other road objects, contact evidence and occlusions. '
    'Do NOT decide whether there is an incident, near miss, emergency braking or collision. '
    'One still image cannot prove movement, speed or causality. '
    'NO_VISIBLE_CONTACT means contact is not visible, not that no incident occurred. '
    'Do not infer hidden causes. Return only the observation JSON schema.'
)


class FrameThenDecisionProvider(LocalQwenProvider):
    two_stage = True

    def _call(self, stage, content, schema, context):
        config = self.config
        request_id = uuid4().hex
        payload = {'model': config.model, 'temperature': 0, 'max_tokens': 768 if stage == 'frame_observation' else config.max_output_tokens,
                   'response_format': {'type': 'json_schema', 'json_schema': {'name': stage, 'strict': True, 'schema': schema}},
                   'messages': [{'role': 'user', 'content': content}]}
        directory = Path(config.requests_dir) if config.requests_dir else None
        if directory:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f'{request_id}.request.json').write_text(json.dumps(payload), encoding='utf-8')
            if context.job_id:
                from backend.services.pipeline_status import update_status
                update_status(directory.parent, context.job_id, 'qwen',
                              'Qwen mô tả từng ảnh; chưa quyết định incident.' if stage == 'frame_observation' else 'Qwen tổng hợp toàn bộ quan sát và telemetry để quyết định.',
                              analysis_stage=stage, request_id=request_id)
        started = time.monotonic()
        raw, decoded, status, error = None, None, None, None
        client = self.client or httpx.Client(trust_env=False)
        try:
            response_bytes = bytearray()
            with client.stream('POST', config.endpoint, json=payload, timeout=config.timeout_s, follow_redirects=False) as response:
                status = response.status_code
                for chunk in response.iter_bytes():
                    response_bytes.extend(chunk)
                    if len(response_bytes) > config.max_output_bytes:
                        raise ValueError('two-stage response exceeded byte budget')
                response.raise_for_status()
            decoded = json.loads(response_bytes)
            raw = decoded['choices'][0]['message']['content']
            return raw, {'request_id': request_id, 'stage': stage, 'input_tokens': decoded.get('usage', {}).get('prompt_tokens'),
                         'output_tokens': decoded.get('usage', {}).get('completion_tokens'), 'latency_s': time.monotonic() - started,
                         'prompt_sha256': hashlib.sha256(content[0]['text'].encode()).hexdigest()}
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            journal = {'request_id': request_id, 'stage': stage, 'http_status': status, 'error': error,
                       'raw_output': raw, 'provider_response': decoded, 'job_id': context.job_id,
                       'recording_id': context.registry.recording_id, 'latency_s': time.monotonic() - started}
            if directory:
                (directory / f'{request_id}.attempt-1.response.json').write_text(json.dumps(journal, ensure_ascii=False), encoding='utf-8')
            if config.outputs_path:
                append_output(config.outputs_path, journal)
            if self.client is None:
                client.close()

    def analyze(self, context):
        if self.settings.qwen_runtime != 'ollama':
            raise ValueError('two-stage analysis requires Ollama')
        ensure_ollama_runtime(self.settings)
        if not 0 < len(context.frames) < 200 or len(context.telemetry_rows) > self.config.max_telemetry_rows:
            raise ValueError('two-stage context exceeds frame/telemetry budget')
        times = [frame.time_start_s for frame in context.frames]
        if times != sorted(set(times)) or any(not 0 <= at < context.duration_s for at in times):
            raise ValueError('two-stage frames must have unique ordered video timestamps')
        observations, usage = [], []
        observation_prompt_hash = hashlib.sha256(OBSERVE_PROMPT.encode()).hexdigest()
        target = Path(self.config.requests_dir) / f'{context.registry.candidate_id}.observations.json' if self.config.requests_dir else None
        cached = {}
        if target and target.exists():
            saved = json.loads(target.read_text(encoding='utf-8'))
            if saved.get('model') == self.config.model and saved.get('revision') == self.config.revision and saved.get('prompt_sha256') == observation_prompt_hash:
                cached = {item['evidence_id']: item for item in saved['observations']}
        reused = 0
        refs = {asset.evidence_id: asset for asset in context.registry.assets}
        total_bytes = 0
        for frame in context.frames:
            if refs.get(frame.evidence_id) != frame or frame.source != 'VIDEO' or (frame.recording_id, frame.candidate_id) != (context.registry.recording_id, context.registry.candidate_id) or file_hash(frame.path) != frame.sha256:
                raise ValueError('frame must match registered immutable visual evidence')
            data = frame.path.read_bytes()
            total_bytes += len(data)
            if total_bytes > self.config.max_image_bytes:
                raise ValueError('two-stage images exceed byte budget')
            saved = cached.get(frame.evidence_id)
            if saved and saved['image_sha256'] == frame.sha256 and saved['time_s'] == frame.time_start_s:
                keys = FrameObservation.model_fields
                FrameObservation.model_validate({key: saved[key] for key in keys})
                observations.append(saved)
                reused += 1
                continue
            content = [{'type': 'text', 'text': OBSERVE_PROMPT},
                       {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(data).decode()}}]
            raw, call = self._call('frame_observation', content, FrameObservation.model_json_schema(), context)
            observation = FrameObservation.model_validate_json(raw)
            observations.append({'evidence_id': frame.evidence_id, 'time_s': frame.time_start_s,
                                 'image_sha256': frame.sha256, 'request_id': call['request_id'], **observation.model_dump()})
            usage.append(call)
            if target:
                target.write_text(json.dumps({'complete': len(observations) == len(context.frames), 'expected_frames': len(context.frames), 'model': self.config.model, 'revision': self.config.revision, 'prompt_sha256': observation_prompt_hash, 'observations': observations}, ensure_ascii=False), encoding='utf-8')
        telemetry = filtered_telemetry(context.telemetry_rows)
        telemetry = sample_telemetry(telemetry, times + [flag['time_s'] for flag in context.flags])
        registry = batch_registry(context)
        facts = {'duration_s': context.duration_s, 'candidate_window': context.candidate_window,
                 'frame_observations': [{k: v for k, v in o.items() if k not in {'description', 'image_sha256', 'request_id'}} for o in observations], 'telemetry': telemetry,
                 'telemetry_units': {'speed': 'm/s', 'acceleration': 'm/s²', 'brake': '0..1'},
                 'flags': context.flags, 'evidence': [{'evidence_id': a.evidence_id, 'source': a.source, 'start_s': a.time_start_s, 'end_s': a.time_end_s} for a in registry.assets]}
        prompt = read_prompt(self.config.prompt_path) if self.config.prompt_path else 'Return an evidence-grounded schema 2.0 DRAFT.'
        prompt += '\nDECISION STAGE: no original images are attached. Use ONLY the ordered per-image observations below and synchronized telemetry. Ignore any incident/no-incident or near-miss verdict accidentally written inside an image description; those are outside the observation task. Infer motion cautiously across observations; never invent objects, contact, damage or injury. Classify pedestrian trajectory conflict/near miss separately from collision. Cite only the supplied evidence IDs at their exact times. Negative observations of contact do not negate braking or near miss. State uncertainty where observations are incomplete. Write Vietnamese.\n' + json.dumps(facts, ensure_ascii=False)
        instructions, facts_json = prompt.rsplit('\n', 1)
        prompt = instructions + '\nEvaluate the trajectory from sidewalk to center lane/in front of ego vehicle, and compare speed before/after the braking interval numerically. Contact is required ONLY for COLLISION, not for HARD_BRAKING or OTHER pedestrian conflict. If detected, use at most 5 representative timeline observations from the relevant interval, not one per frame. If negative, window MUST be null and timeline/factors empty; explain unresolved strong telemetry in unknowns.\n' + facts_json
        raw, call = self._call('incident_decision', [{'type': 'text', 'text': prompt}], detection_output_schema(), context)
        usage.append(call)
        analysis = AIIncidentAnalysisV2.model_validate_json(raw, context={'video_duration_s': context.duration_s})
        validate_analysis(analysis, registry, context.duration_s)
        if analysis.event_type == 'COLLISION' and not any(o['contact_evidence'] == 'VISIBLE_CONTACT' for o in observations):
            raise ValueError('decision claims collision without observed contact')
        return ProviderResult(analysis, {'analysis_mode': 'frames_then_decision', 'model': self.config.model,
                                        'revision': self.config.revision, 'provider': 'self_hosted',
                                        'input_hashes': [f.sha256 for f in context.frames], 'observations': observations,
                                        'prompt_sha256': call['prompt_sha256'], 'prompt_version': 'frames-then-decision-1'},
                              {'attempts': len(usage), 'reused_observations': reused, 'latency_s': sum(item['latency_s'] for item in usage), 'stages': usage})
