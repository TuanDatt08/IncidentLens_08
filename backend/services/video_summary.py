"""Grounded, bounded final video synthesis shared by both GPU worker paths."""
import base64
import hashlib
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from backend.services.prompt_io import append_output, read_prompt


class SummaryEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    candidate_ids: list[str] = Field(min_length=1)
    status: Literal['CONFIRMED', 'INCONCLUSIVE']
    event_type: str = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=1200)
    evidence_ids: list[str]


class VideoSummary(BaseModel):
    model_config = ConfigDict(extra='forbid')
    overall_status: Literal['CONFIRMED', 'INCONCLUSIVE', 'NO_INCIDENT_IN_OBSERVED_COVERAGE']
    summary: str = Field(min_length=1, max_length=2400)
    events: list[SummaryEvent]
    unknowns: list[str]
    review_status: Literal['DRAFT']


def preserve_summary_coverage(data, records):
    """A model omission stays unresolved; it never erases a suspected event."""
    result = VideoSummary.model_validate(data).model_dump()
    covered = {key for event in result['events'] for key in event['candidate_ids']}
    for record in records:
        identity = record['candidate_id']
        if record['status'] not in {'CONFIRMED', 'INCONCLUSIVE'} or identity in covered:
            continue
        result['events'].append({'candidate_ids': [identity], 'status': 'INCONCLUSIVE',
            'event_type': record.get('event_type', 'UNKNOWN'),
            'summary': 'Chưa đối chiếu đủ trong kết luận cuối: ' + record.get('summary', 'Cần xem lại bằng chứng.')[:1000],
            'evidence_ids': record.get('evidence_ids', [])})
        result['unknowns'].append(f'SUMMARY_OMITTED_CANDIDATE: {identity} được giữ lại để review, không coi là âm tính.')
    if result['events'] and not any(event['status']=='CONFIRMED' for event in result['events']):
        result['overall_status'] = 'INCONCLUSIVE'
    return result


def validate_summary(data, records, evidence_ids, coverage_unknowns):
    result = VideoSummary.model_validate(data).model_dump()
    by_id = {record['candidate_id']: record for record in records}
    covered = set()
    for event in result['events']:
        if not set(event['evidence_ids']) <= set(evidence_ids):
            raise ValueError('summary invented evidence')
        if not set(event['candidate_ids']) <= by_id.keys():
            raise ValueError('summary invented candidate')
        sources = [by_id[key] for key in event['candidate_ids']]
        allowed = {eid for record in sources for eid in record.get('evidence_ids', [])}
        if not set(event['evidence_ids']) <= allowed:
            raise ValueError('summary evidence belongs to a different candidate')
        if event['status'] == 'CONFIRMED' and (not event['evidence_ids'] or not any(
                record['status'] == 'CONFIRMED'
                and record.get('event_type', event['event_type']) == event['event_type']
                and set(event['evidence_ids']) & set(record.get('confirmation_evidence_ids', record.get('evidence_ids', [])))
                for record in sources)):
            raise ValueError('summary cannot promote an unconfirmed candidate')
        covered.update(event['candidate_ids'])
    required = {key for key, record in by_id.items() if record['status'] in {'CONFIRMED', 'INCONCLUSIVE'}}
    if required - covered:
        raise ValueError('summary omitted unresolved or confirmed candidate')
    result['unknowns'] = list(dict.fromkeys([*result['unknowns'], *coverage_unknowns]))
    expected = 'CONFIRMED' if any(event['status'] == 'CONFIRMED' for event in result['events']) else 'INCONCLUSIVE' if result['events'] or coverage_unknowns or result['overall_status']=='INCONCLUSIVE' else 'NO_INCIDENT_IN_OBSERVED_COVERAGE'
    if result['overall_status'] != expected:
        if expected == 'INCONCLUSIVE':
            result['overall_status'] = expected
        else:
            raise ValueError('summary status contradicts its events')
    return result


def summarize_video(records, *, evidence, coverage, settings, output, job_id, clock=None, request_budget=200):
    """Keep all sequence notes; oversize/failed synthesis remains explicitly unresolved."""
    prompt = read_prompt(settings.qwen_summary_prompt_path)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    output = Path(output)
    directory = output / 'requests'
    directory.mkdir(parents=True, exist_ok=True)
    unknowns = list(coverage.get('unresolved', []))
    calls = 0
    # Candidate-only coverage must never become a video-wide absence claim.
    if not coverage.get('sampled_entire_video', False):
        unknowns.append('Chỉ xem các vùng candidate; phần còn lại của video chưa được phân tích.')
    refs = {asset.evidence_id: {'evidence_id': asset.evidence_id,
            ('frame_seq' if clock else 't_video_s'): clock.position(asset.time_start_s) if clock else asset.time_start_s,
            'source': asset.source} for asset in evidence if asset.source == 'VIDEO' and asset.frame_order is not None}
    refs.update({asset.evidence_id: {'evidence_id': asset.evidence_id, 'source': 'TELEMETRY',
                 'start_t_video_s': asset.time_start_s, 'end_t_video_s': asset.time_end_s}
                 for asset in evidence if asset.source == 'TELEMETRY'})
    # Use bounded hierarchical reduction; every original note remains in a request journal.
    def synthesize(group, images, phase, feedback=None):
        nonlocal calls
        if calls >= request_budget:
            raise ValueError('final synthesis request budget exhausted')
        calls += 1
        request_id = uuid4().hex
        context = {'decision_scope': phase, 'input_mode': 'VIDEO_ONLY' if clock else 'VIDEO_WITH_SYNCED_LOG',
                   'coordinate': 'frame_seq' if clock else 't_video_s', 'records': group,
                   'coverage': coverage, 'coverage_unknowns': unknowns,
                   'evidence': [refs[eid] for eid in dict.fromkeys(eid for record in group for eid in record.get('evidence_ids', [])) if eid in refs]}
        context['allowed_confirmed_candidates'] = [record['candidate_id'] for record in group if record['status']=='CONFIRMED']
        context['must_account_for_candidates'] = [record['candidate_id'] for record in group if record['status'] in {'CONFIRMED', 'INCONCLUSIVE'}]
        if feedback:
            context['validation_feedback'] = feedback
        text = json.dumps(context, ensure_ascii=False, separators=(',', ':'))
        if len(text.encode()) > 70000:
            raise ValueError('summary context budget exceeded; no notes silently discarded')
        content = [{'type': 'text', 'text': text}]
        for asset in images:
            content.extend([{'type': 'text', 'text': json.dumps(refs[asset.evidence_id])},
                            {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(asset.path.read_bytes()).decode()}}])
        content.append({'type': 'text', 'text': 'Trả JSON đúng schema; tất cả summary và unknowns phải là tiếng Việt có dấu. Giữ nguyên evidence_id, candidate_ids và tọa độ được cung cấp.'})
        schema = VideoSummary.model_json_schema()
        event_schema = schema['$defs']['SummaryEvent']['properties']
        event_schema['candidate_ids']['items']['enum'] = [record['candidate_id'] for record in group]
        event_schema['evidence_ids']['items']['enum'] = [item['evidence_id'] for item in context['evidence']] or ['NO_EVIDENCE_DO_NOT_CITE']
        if not context['allowed_confirmed_candidates']:
            event_schema['status'] = {'const': 'INCONCLUSIVE', 'type': 'string'}
            schema['properties']['overall_status']['enum'] = ['INCONCLUSIVE', 'NO_INCIDENT_IN_OBSERVED_COVERAGE']
        payload = {'model': settings.qwen_ollama_model, 'temperature': 0, 'max_tokens': 4096,
                   'response_format': {'type': 'json_schema', 'json_schema': {'name': 'video_summary', 'strict': True, 'schema': schema}},
                   'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}],
                   **({'reasoning_effort': settings.qwen_reasoning_effort} if settings.qwen_reasoning_effort else {})}
        (directory / f'{request_id}.request.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        raw = None
        error = None
        try:
            with httpx.Client(trust_env=False, timeout=settings.qwen_timeout_s) as client:
                response = client.post(settings.qwen_endpoint, json=payload)
            (directory / f'{request_id}.response.json').write_text(response.text, encoding='utf-8')
            response.raise_for_status()
            raw = response.json()['choices'][0]['message']['content']
            return validate_summary(preserve_summary_coverage(json.loads(raw), group), group, refs.keys(), unknowns)
        except ValueError as exc:
            error = str(exc)
            if feedback is None:
                return synthesize(group, images, phase,
                                  {'error': error, 'previous_invalid_output': raw, 'instruction': 'Sửa JSON và dẫn chứng theo lỗi; không bịa thêm bằng chứng.'})
            raise
        except (KeyError, IndexError, httpx.HTTPError) as exc:
            error = str(exc)
            raise
        finally:
            append_output(output / 'outputs.txt', {'request_id': request_id, 'job_id': job_id, 'stage': phase,
                          'model': settings.qwen_ollama_model, 'prompt': prompt, 'prompt_sha256': prompt_hash,
                          'raw_output': raw, 'error': error})

    originals = records
    lineage = {record['candidate_id']: [record['candidate_id']] for record in records}
    try:
        level = 0
        while len(records) > 8:
            reduced = []
            for index in range(0, len(records), 8):
                group = records[index:index + 8]
                partial = synthesize(group, [], 'SUMMARY_GROUP')
                for event_index, event in enumerate(partial['events']):
                    identity = f'GROUP-{level}-{index}-{event_index}'
                    lineage[identity] = list(dict.fromkeys(key for source in event['candidate_ids'] for key in lineage[source]))
                    reduced.append({'candidate_id': identity, **event,
                                    'source_records': event['candidate_ids']})
                if not partial['events']:
                    identity = f'GROUP-{level}-{index}'
                    lineage[identity] = [key for record in group for key in lineage[record['candidate_id']]]
                    reduced.append({'candidate_id': identity, 'status': 'NO_INCIDENT',
                                    'summary': partial['summary'], 'unknowns': partial['unknowns'], 'evidence_ids': [],
                                    'source_records': [r['candidate_id'] for r in group]})
                unknowns[:] = list(dict.fromkeys([*unknowns, *partial['unknowns']]))
            if len(reduced) >= len(records):
                raise ValueError('summary cannot reduce within context budget')
            records = reduced
            level += 1
        frames = sorted({a.evidence_id: a for a in evidence if a.source == 'VIDEO' and a.frame_order is not None}.values(), key=lambda a: a.time_start_s)
        cited = {eid for record in records if record['status'] != 'NO_INCIDENT' for eid in record.get('evidence_ids', [])}
        selected = [a for a in frames if a.evidence_id in cited] or frames
        images = [selected[i] for i in sorted({round(i * (len(selected) - 1) / 5) for i in range(6)})] if selected else []
        result = synthesize(records, images, 'FINAL_VIDEO')
        for event in result['events']:
            event['candidate_ids'] = list(dict.fromkeys(key for source in event['candidate_ids'] for key in lineage[source]))
        result = validate_summary(result, originals, refs.keys(), unknowns)
        result['input_record_ids'] = [record['candidate_id'] for record in originals]
        result['evidence'] = [refs[eid] for eid in dict.fromkeys(eid for event in result['events'] for eid in event['evidence_ids'])]
    except (ValueError, KeyError, IndexError, httpx.HTTPError) as exc:
        result = {'overall_status': 'INCONCLUSIVE', 'summary': 'Chưa hoàn tất tổng hợp toàn video; cần kỹ sư kiểm tra các kết quả và bằng chứng.',
                  'events': [], 'unknowns': [*unknowns, f'FINAL_VIDEO_FAILED: {exc}'], 'review_status': 'DRAFT', 'error': type(exc).__name__}
    (output / f'{job_id or "analysis"}.video-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
