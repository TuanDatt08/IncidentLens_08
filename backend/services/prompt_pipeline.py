"""Run the editable Stage A/B contracts and preserve the complete model response."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

import httpx
from pydantic import ConfigDict, Field, create_model

from backend.models.contracts import AnalysisResult, EvidenceV1
from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.log_normalization import normalize_log
from backend.services.pipeline_status import update_status
from backend.services.processing import InsufficientEvidence, ProcessedResult
from backend.services.prompt_io import append_output, read_prompt
from backend.services.qwen_local import ensure_ollama_runtime
from backend.services.synchronization import TimeAnchor, align
from backend.services.video import VideoService
from backend.services.vlm_provider import compact_records, sample_telemetry

NonblankText = Annotated[str, Field(min_length=1, pattern=r'\S')]


def prompt_contracts(text: str) -> dict:
    """The JSON examples in the user's prompt are the single contract source."""
    sections = text.split('## STAGE ')
    result = {}
    for section in sections[1:]:
        stage = section[0]
        section = section.split('## BACKEND RULES')[0]
        marker = section.index('{\n')
        template, _ = json.JSONDecoder().raw_decode(section[marker:])
        event_types = ('COLLISION', 'NEAR_COLLISION', 'UNSAFE_CUT_IN', 'ABRUPT_OBSTACLE_AVOIDANCE', 'PEDESTRIAN_CONFLICT', 'LANE_DEPARTURE', 'ROAD_HAZARD', 'LOSS_OF_CONTROL', 'OTHER', 'UNKNOWN')
        def model(value, name, key=''):
            if isinstance(value, dict):
                return create_model(name, __config__=ConfigDict(extra='forbid', strict=True, allow_inf_nan=False), **{k: (model(v, name + k.title(), k), ...) for k, v in value.items()})
            if isinstance(value, list):
                return list[model(value[0], name + 'Item')] if value else list[NonblankText]
            if value is None:
                return bool | None if key in {'collision_occurred', 'near_miss_occurred', 'incident_resolved', 'time_sync_reliable'} else float | None if key.endswith('_s') else NonblankText | None
            if isinstance(value, bool):
                return bool
            if isinstance(value, (float, int)):
                return Annotated[float, Field(ge=0, le=1)] if key == 'confidence' else Annotated[float, Field(ge=0)]
            if key in {'schema_version', 'review_status', 'time_basis'}:
                return Literal.__getitem__((value,))
            if key == 'event_type':
                return Literal.__getitem__(event_types)
            if ' | ' in value:
                return Literal.__getitem__(tuple(value.split(' | ')))
            return NonblankText
        result[stage] = ('## STAGE ' + section, model(template, 'Stage' + stage))
    if set(result) != {'A', 'B'}:
        raise ValueError('promt.txt must contain both Stage A and Stage B JSON contracts')
    return result


def validate_stage(data: dict, model, registry: dict, duration: float) -> dict:
    parsed = model.model_validate_json(json.dumps(data)).model_dump(mode='json')
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith('_s') and item is not None and (not isinstance(item, (float, int)) or not math.isfinite(item) or not 0 <= item <= duration):
                    raise ValueError('timestamp exceeds source video')
            if 'evidence_id' in value:
                asset = registry.get(value['evidence_id'])
                if asset is None:
                    raise ValueError('unknown evidence ID')
                if not asset.time_start_s - 0.001 <= value['time_s'] <= asset.time_end_s + 0.001:
                    raise ValueError('evidence timestamp mismatch')
                expected = 'VIDEO_FRAME' if asset.source == 'VIDEO' else 'LOG'
                if value.get('source', expected) != expected:
                    raise ValueError('evidence source mismatch')
            for eid in value.get('evidence_ids', []):
                if eid not in registry:
                    raise ValueError('unknown evidence ID')
                if 'time_s' in value and not registry[eid].time_start_s - .001 <= value['time_s'] <= registry[eid].time_end_s + .001:
                    raise ValueError('timeline evidence timestamp mismatch')
            if value.get('certainty') in {'OBSERVED', 'SUPPORTED_INFERENCE'} and 'evidence_ids' in value and not value['evidence_ids']:
                raise ValueError('supported timeline requires evidence')
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(parsed)
    if parsed.get('overall_status') == 'NO_INCIDENT' and parsed['incidents']:
        raise ValueError('NO_INCIDENT must have empty incidents')
    if parsed.get('overall_status') == 'CONFIRMED' and not any(event['status'] == 'CONFIRMED' for event in parsed['incidents']):
        raise ValueError('CONFIRMED overall status requires a confirmed incident')
    for event in parsed.get('incidents', []):
        points = [event[k] for k in ('onset_s', 'critical_s', 'end_s')]
        known = [v for v in points if v is not None]
        if known != sorted(known):
            raise ValueError('incident times out of order')
        if event['status'] == 'CONFIRMED' and (event['onset_s'] is None or event['critical_s'] is None or not event['evidence']):
            raise ValueError('confirmed detection requires onset, critical and evidence')
        if event['status'] == 'CONFIRMED' and len({item['evidence_id'] for item in event['evidence']}) < 2:
            raise ValueError('confirmed detection requires corroborating distinct evidence')
    if 'timing' in parsed:
        timing = parsed['timing']
        if timing['clip_start_s'] >= timing['clip_end_s']:
            raise ValueError('clip requires positive duration')
        known = [timing[k] for k in ('onset_s', 'critical_s', 'end_s') if timing[k] is not None]
        if known != sorted(known) or any(not timing['clip_start_s'] <= t <= timing['clip_end_s'] for t in known):
            raise ValueError('analysis timing outside clip or out of order')
        if parsed['analysis_status'] == 'CONFIRMED' and (not parsed['evidence'] or timing['onset_s'] is None or timing['critical_s'] is None):
            raise ValueError('confirmed analysis requires evidence and timing')
        if parsed['event_type'] == 'COLLISION' and parsed['analysis_status'] == 'CONFIRMED' and not any(e['source'] == 'VIDEO_FRAME' and e['certainty'] == 'OBSERVED' for e in parsed['evidence']):
            raise ValueError('collision requires observed video evidence')
    return parsed


def process_prompt_incident(incident, *, storage_root, settings, job_id, on_progress=None):
    root = Path(storage_root).resolve()
    output = root / incident['incident_id'] / 'output'
    output.mkdir(parents=True, exist_ok=True)
    def status(stage, message, **kw):
        return update_status(output, job_id, stage, message, **kw)
    status('backend', 'Backend đọc video, CSV và kiểm tra đồng bộ thời gian.')
    source = (root / incident['video_uri']).resolve()
    if root not in source.parents:
        raise ValueError('video outside storage')
    duration = incident['video_metadata']['duration']
    fps = incident['video_metadata']['fps']
    service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin, max_output_bytes=2 * 1024**3, frame_max_width=640)
    text = read_prompt(settings.qwen_prompt_path)
    contracts = prompt_contracts(text)
    snapshot = output / f'{job_id}.prompt.txt'
    snapshot.write_text(text, encoding='utf-8')
    prompt_hash = hashlib.sha256(text.encode()).hexdigest()
    inputs = [{'uri': source.relative_to(root).as_posix(), 'sha256': file_hash(source), 'bytes': source.stat().st_size}]
    for name in ('telemetry.csv', 'sync-metadata.json'):
        path = source.parent / name
        if path.is_file():
            inputs.append({'uri': path.relative_to(root).as_posix(), 'sha256': file_hash(path), 'bytes': path.stat().st_size})
    service.write_json(output / f'{job_id}.input.json', {'input_files': inputs, 'video_metadata': incident['video_metadata'], 'prompt_sha256': prompt_hash})
    rows, unsynced_rows, limitations, evidence, registry = [], [], [], [], {}
    alignment = {'quality': 'UNKNOWN', 'unknowns': ['Không có log đi kèm.']}
    if incident.get('telemetry_uri'):
        log_path = (root / incident['telemetry_uri']).resolve()
        if root not in log_path.parents:
            raise ValueError('log outside storage')
        log = normalize_log(log_path)
        anchors = [TimeAnchor(**item) for item in incident['video_metadata'].get('anchors', [])]
        offset = incident['video_metadata'].get('log_offset_s', settings.qwen_v1_log_offset_s)
        if not anchors and offset is not None:
            anchors = [TimeAnchor(-offset, 0., 'explicit_upload_offset'), TimeAnchor(duration-offset, duration, 'explicit_upload_offset')]
        mapping = align(incident['video_metadata'], log, anchors)
        alignment = asdict(mapping)
        for row in log.iter_rows():
            if mapping.quality == 'VERIFIED':
                at = mapping.to_video_seconds(row['time_s'])
                if 0 <= at <= duration:
                    rows.append({**row, 'time_s': at})
            else:
                unsynced_rows.append(row)
        if not rows:
            limitations.append('CSV chưa đồng bộ: chỉ cung cấp log theo đồng hồ gốc, không ghép sự kiện log với frame hoặc suy mốc chính xác.')
        else:
            log_file = output / f'{job_id}.telemetry.json'
            service.write_json(log_file, rows)
            asset = EvidenceAsset('LOG-' + file_hash(log_file)[:16], incident['incident_id'], 'all', log_file, file_hash(log_file), rows[0]['time_s'], rows[-1]['time_s'], 'TELEMETRY', 'application/json')
            registry[asset.evidence_id] = asset
            evidence.append(asset)
    service.write_json(output / f'{job_id}.alignment.json', alignment)
    limitations.append('Chỉ phân tích các frame được cung cấp; diễn biến giữa các frame chưa được quan sát liên tục.')
    ensure_ollama_runtime(settings)
    calls, detections, analyses = [], [], []
    log_sample_times = [unsynced_rows[0]['time_s'], unsynced_rows[-1]['time_s']] if unsynced_rows else []
    for signal in ('brake', 'acceleration', 'collision_intensity'):
        available = [row for row in unsynced_rows if row.get(signal) not in (None, '')]
        if available:
            log_sample_times.append(max(available, key=lambda row: abs(float(row[signal])))['time_s'])
    def frames(start, end, label, critical=None):
        last = min(end, max(0., duration - 1.5/fps))
        times = [round(start+i/settings.qwen_sampling_fps, 6) for i in range(math.floor((last-start)*settings.qwen_sampling_fps)+1)]
        if len(times) > 256:
            raise InsufficientEvidence('Frame extraction budget exceeded.')
        selected = {min(times, key=lambda t: abs(t-(start+(last-start)*i/3))) for i in range(4)}
        if critical is not None:
            interior = list(sorted(selected))[1:-1] or list(selected)
            replace_at = min(interior, key=lambda t: abs(t-critical))
            selected.remove(replace_at)
            selected.add(min(times, key=lambda t: abs(t-critical)))
        assets = []
        for index, at in enumerate(sorted(times)):
            path = output / 'frames' / f'{job_id}-{label}-{index}.jpg'
            service.extract_frame(source, at, path)
            asset = EvidenceAsset('FRAME-' + file_hash(path)[:16] + '-' + str(at), incident['incident_id'], label, path, file_hash(path), at, at, 'VIDEO', 'image/jpeg', index)
            registry[asset.evidence_id] = asset
            evidence.append(asset)
            if at in selected:
                assets.append(asset)
        return assets
    def call(stage, images, start, end, extra=None, attempt=1):
        if len(calls) >= 200:
            raise InsufficientEvidence('Model call budget exhausted; remaining windows are unreviewed.')
        prompt, model = contracts[stage]
        request_id = uuid4().hex
        status('prompt', f'Nạp prompt Stage {stage}.', model=settings.qwen_ollama_model, prompt_path=settings.qwen_prompt_path, prompt_sha256=prompt_hash, prompt_text=prompt, request_id=request_id, stage_name=stage, alignment=alignment)
        sampled = sample_telemetry(rows, [a.time_start_s for a in images])
        refs = [{'evidence_id': a.evidence_id, 'time_s': a.time_start_s, 'end_s': a.time_end_s, 'source': 'VIDEO_FRAME' if a.source == 'VIDEO' else 'LOG'} for a in [*images, *[a for a in registry.values() if a.source == 'TELEMETRY']]]
        context = {'recording_id': incident['incident_id'], 'video_duration_s': duration, 'clip_start_s': start, 'clip_end_s': end, 'time_basis': 'video_seconds', 'extraction_fps': settings.qwen_sampling_fps, 'sample_rate_fps': None, 'frame_times_s': [a.time_start_s for a in images], 'telemetry': compact_records(sampled), 'unsynchronized_log': {'time_basis': 'incident_relative', 'row_count': len(unsynced_rows), **compact_records(sample_telemetry(unsynced_rows, log_sample_times))}, 'alignment': alignment, 'evidence': refs, 'coverage_limitations': limitations, **(extra or {})}
        content = [{'type': 'text', 'text': json.dumps(context, ensure_ascii=False)}, *[{'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(a.path.read_bytes()).decode()}} for a in images]]
        payload = {'model': settings.qwen_ollama_model, 'temperature': 0, 'max_tokens': 4096, 'response_format': {'type': 'json_schema', 'json_schema': {'name': 'stage_' + stage, 'strict': True, 'schema': model.model_json_schema()}}, 'messages': [{'role': 'system', 'content': prompt + '\nMọi mô tả, tóm tắt, nguyên nhân và giới hạn phải viết bằng tiếng Việt có dấu. Không bỏ qua coverage_limitations; thêm vào unknowns hoặc data_quality.limitations.'}, {'role': 'user', 'content': content}]}
        req_dir = output / 'requests'
        req_dir.mkdir(exist_ok=True)
        service.write_json(req_dir / f'{request_id}.request.json', payload)
        status('qwen', f'Model Qwen 7B đang phân tích Stage {stage}, {len(images)} frame.', request_id=request_id, frame_times_s=context['frame_times_s'], stage_name=stage)
        began = time.monotonic()
        raw = None
        response = None
        failure = None
        try:
            with httpx.Client(trust_env=False, timeout=settings.qwen_timeout_s) as client:
                response = client.post(settings.qwen_endpoint, json=payload)
            service.write_json(req_dir / f'{request_id}.response.json', {'http_status': response.status_code, 'body': response.text})
            response.raise_for_status()
            envelope = response.json()
            raw = envelope['choices'][0]['message']['content']
            status('validation', f'Backend kiểm tra JSON, thời gian và evidence Stage {stage}.', usage=envelope.get('usage', {}), latency_s=time.monotonic()-began)
            allowed = {a.evidence_id: a for a in [*images, *[a for a in registry.values() if a.source == 'TELEMETRY']]}
            parsed = validate_stage(json.loads(raw), model, allowed, duration)
            if stage == 'A':
                if abs(parsed['video_duration_s']-duration) > .01:
                    raise ValueError('model changed source duration')
                if not parsed['analyzed_intervals'] or any(not start <= item['start_s'] < item['end_s'] <= end for item in parsed['analyzed_intervals']):
                    raise ValueError('analyzed intervals exceed the supplied detection window')
                if any(not start <= event[key] <= end for event in parsed['incidents'] for key in ('onset_s', 'critical_s', 'end_s') if event[key] is not None):
                    raise ValueError('detected event time exceeds the supplied window')
            elif abs(parsed['timing']['clip_start_s']-start) > .001 or abs(parsed['timing']['clip_end_s']-end) > .001:
                raise ValueError('model changed extracted clip bounds')
            descriptions = [parsed.get('summary', ''), *parsed.get('coverage_limitations', []), *[event['event_summary'] for event in parsed.get('incidents', [])]]
            summaries = [parsed['summary']] if 'summary' in parsed else [event['event_summary'] for event in parsed.get('incidents', [])]
            if not any(re.search('[À-ỹ]', item) for item in descriptions) or any(not re.search('[À-ỹ]', item) for item in summaries):
                raise ValueError('Mô tả phải bằng tiếng Việt có dấu; bổ sung giới hạn coverage thật.')
            record = {'request_id': request_id, 'stage': stage, 'prompt_sha256': prompt_hash, 'frame_times_s': context['frame_times_s'], 'usage': envelope.get('usage', {}), 'latency_s': time.monotonic()-began, 'output': parsed}
            calls.append(record)
            service.write_json(output / f'{job_id}.calls.json', calls)
            return parsed
        except ValueError as exc:
            failure = f'{type(exc).__name__}: {exc}'
            if attempt >= 2:
                raise
        except Exception as exc:
            failure = f'{type(exc).__name__}: {exc}'
            raise
        finally:
            entry = {'request_id': request_id, 'job_id': job_id, 'stage': stage, 'model': settings.qwen_ollama_model, 'prompt': prompt, 'prompt_sha256': prompt_hash, 'raw_output': raw, 'latency_s': time.monotonic()-began, 'http_status': response.status_code if response is not None else None, 'error': failure}
            append_output(output / 'outputs.txt', entry)
            append_output(settings.qwen_outputs_path, entry)
        status('validation', 'Output chưa đạt; yêu cầu Qwen sửa một lần, giữ nguyên raw output.', validation_error=failure)
        return call(stage, images, start, end, {**(extra or {}), 'validation_feedback': failure, 'previous_invalid_output': raw}, attempt+1)
    # Overlapping 8-second windows preserve temporal context on CPU.
    starts = [float(t) for t in range(0, max(1, math.ceil(duration-2)), 6)]
    if len(starts) > 30:
        raise InsufficientEvidence('Video exceeds 30 detection windows; segment it before analysis.')
    seen_candidates, duplicate_candidates = {}, []
    for index, start in enumerate(starts):
        end = min(duration, start+8.)
        status('backend', 'Backend trích frame theo thứ tự thời gian.', window=[start, end])
        images = frames(start, end, f'A{index}')
        detection = call('A', images, start, end)
        if abs(detection['video_duration_s']-duration) > .01:
            raise ValueError('model changed source duration')
        detection['coverage_limitations'] = list(dict.fromkeys([*detection['coverage_limitations'], *limitations]))
        detections.append(detection)
        service.write_json(output / f'{job_id}.stage-a.json', detections)
        if len(detection['incidents']) > 5:
            raise InsufficientEvidence('Too many candidates in one window; engineer review is required.')
        for event in detection['incidents']:
            # Only identical known-time candidates are safe to consolidate automatically.
            key = (event['event_type'], event['onset_s'], event['critical_s'], event['end_s'], event['event_summary'].strip())
            if event['onset_s'] is not None and event['critical_s'] is not None:
                if key in seen_candidates:
                    duplicate_candidates.append({'window_index': index, 'candidate': event, 'stage_b_index': seen_candidates[key]})
                    continue
                seen_candidates[key] = len(analyses)
            onset, critical, finish = event['onset_s'], event['critical_s'], event['end_s']
            clip_start = max(0., onset-5) if onset is not None else start
            clip_end = min(duration, finish+3) if finish is not None else min(duration, end+3)
            if clip_start >= clip_end:
                raise ValueError('invalid model clip window')
            status('backend', 'Backend cắt clip và chuẩn bị Stage B.', window=[clip_start, clip_end])
            clip = output / 'clips' / f'{job_id}-{len(analyses)}.mp4'
            service.extract_clip(source, clip_start, clip_end, clip)
            asset = EvidenceAsset('CLIP-' + file_hash(clip)[:16], incident['incident_id'], 'B', clip, file_hash(clip), clip_start, clip_end, 'VIDEO', 'video/mp4')
            evidence.append(asset)
            images = frames(clip_start, clip_end, f'B{len(analyses)}', critical)
            report = call('B', images, clip_start, clip_end, {'candidate': event})
            if abs(report['timing']['clip_start_s']-clip_start) > .001 or abs(report['timing']['clip_end_s']-clip_end) > .001:
                raise ValueError('model changed extracted clip bounds')
            report['unknowns'] = list(dict.fromkeys([*report['unknowns'], *limitations]))
            report['data_quality'].update(video_coverage='PARTIAL', telemetry_available=bool(rows), time_sync_reliable=True if rows else None)
            analyses.append(report)
            service.write_json(output / f'{job_id}.stage-b.json', analyses)
        if on_progress:
            on_progress(2, index+1, len(starts))
    confirmed = [a for a in analyses if a['analysis_status']=='CONFIRMED']
    service.write_json(output / f'{job_id}.stage-b.json', analyses)
    detection_state = 'CONFIRMED' if confirmed else 'INCONCLUSIVE' if analyses or any(d['overall_status'] != 'NO_INCIDENT' for d in detections) else 'NO_INCIDENT_IN_ANALYZED_COVERAGE'
    bundle = {'job_id': job_id, 'schema_version': 'incident_pipeline_v3', 'review_status': 'DRAFT', 'detection_state': detection_state, 'alignment': alignment, 'prompt_path': settings.qwen_prompt_path, 'prompt_sha256': prompt_hash, 'stage_a': detections, 'stage_b': analyses, 'calls': calls, 'unknowns': limitations, 'requires_engineer_review': True}
    bundle['evidence_registry'] = [{'evidence_id': a.evidence_id, 'uri': a.path.relative_to(root).as_posix(), 'sha256': a.sha256, 'start_s': a.time_start_s, 'end_s': a.time_end_s} for a in evidence]
    bundle['input_files'] = inputs
    bundle['consolidated_duplicates'] = duplicate_candidates
    service.write_json(output / f'{job_id}.draft-v3.json', bundle)
    offset = confirmed[0]['timing']['critical_s'] if confirmed else 0.
    def legacy_asset(a):
        return EvidenceV1(evidence_id=a.evidence_id, kind='telemetry' if a.source=='TELEMETRY' else 'video' if a.media_type=='video/mp4' else 'frame', uri=a.path.relative_to(root).as_posix(), sha256=a.sha256, time_range_s=(a.time_start_s-offset,a.time_end_s-offset), bytes=a.path.stat().st_size, media_type=a.media_type)
    metadata = {'provider': 'ollama', 'model': settings.qwen_ollama_model, 'draft_v3': bundle, 'requires_engineer_review': True, 'video_offset_s': offset, 'detection_state': detection_state, 'unknowns': limitations}
    kwargs = {}
    if confirmed:
        first = confirmed[0]
        kwargs = {'incident_type': first['event_type'], 'incident_window': {'start': first['timing']['onset_s']-offset, 'critical': 0., 'end': (first['timing']['end_s'] if first['timing']['end_s'] is not None else first['timing']['clip_end_s'])-offset}, 'summary': '\n'.join(a['summary'] for a in analyses), 'timeline': [{**t, 'time_s': t['time_s']-offset} for a in analyses for t in a['timeline']], 'unknowns': limitations}
    status('database', 'Lưu draft đầy đủ và evidence vào database; chờ kỹ sư review.')
    return ProcessedResult(AnalysisResult(incident_detected=bool(confirmed), model_metadata=metadata, **kwargs), [legacy_asset(a) for a in {a.evidence_id:a for a in evidence}.values()] if confirmed else [], offset if confirmed else None)
