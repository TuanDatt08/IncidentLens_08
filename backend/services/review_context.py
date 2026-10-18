"""Read-only companion data for uncertain reports and synchronized charts."""
from __future__ import annotations

import json
import math

from backend.config import get_settings
from backend.errors import ApiError
from backend.services.access import Principal, require_permission
from backend.services.analysis_details import structured_telemetry_analysis
from backend.services.incidents import get_incident
from backend.services.log_normalization import normalize_log
from backend.services.media import _resolve_asset
from backend.services.reports import get_model_metadata
from backend.services.synchronization import TimeAnchor, align


def chart_points(rows):
    points = [{'time_s': row['time_s'], 'speed_kmh': float(row['speed']) * 3.6 if 'speed' in row else None,
               'brake_pct': float(row['brake']) * 100 if 'brake' in row else None,
               'acceleration': float(row['acceleration']) if 'acceleration' in row else None} for row in rows]
    if len(points) <= 600:
        return points
    selected = {0, len(points) - 1}
    size = math.ceil(len(points) / 99)
    for start in range(0, len(points), size):
        indexes = list(range(start, min(len(points), start + size)))
        for key in ('speed_kmh', 'brake_pct', 'acceleration'):
            valid = [i for i in indexes if points[i][key] is not None]
            if valid:
                selected.update((min(valid, key=lambda i: points[i][key]), max(valid, key=lambda i: points[i][key])))
    return [points[i] for i in sorted(selected)]


def get_review_context(incident_id, *, principal: Principal):
    require_permission(principal, "incident:read")
    incident = get_incident(incident_id)
    metadata = get_model_metadata(incident_id)
    draft = metadata.get('draft_v3') or metadata.get('draft_v2') or {}
    # V3 stores several independent analyses in a pipeline bundle. Expose the
    # original validated objects without rebasing their video timestamps or
    # mixing model suggestions into the engineer's editable report.
    analyses = [item for item in draft.get('stage_b', []) if isinstance(item, dict)]
    if draft.get('schema_version') == 'incident_analysis_v3':
        analyses = [draft]
    if not analyses:
        analyses = metadata.get('structured_analyses') or []
        if not analyses and draft and not metadata.get('draft_v3'):
            analyses = [structured_telemetry_analysis(draft,
                telemetry_available=bool(incident.get('telemetry_uri')),
                unresolved=str(metadata.get('detection_state', '')).startswith('REVIEW_REQUIRED'))]
    primary_analysis = next((item for item in analyses if item.get('analysis_status') == 'CONFIRMED'), analyses[0] if analyses else None)
    summary = primary_analysis.get('summary') if primary_analysis else draft.get('summary')
    warnings = list(dict.fromkeys([*(draft.get('unknowns') or metadata.get('unknowns', [])),
                                  *(warning for item in analyses for warning in item.get('unknowns', []))]))
    checks = metadata.get('consistency_checks', [])
    result = {'review_required': str(metadata.get('detection_state', '')).startswith('REVIEW_REQUIRED') or any('MODEL_TELEMETRY_CONFLICT' in str(item) for item in metadata.get('unknowns', [])),
              'detection_state': metadata.get('detection_state'), 'summary': summary, 'model_output': draft,
              'analyses': analyses, 'primary_analysis': primary_analysis,
              'warnings': warnings, 'consistency_checks': checks,
              'time_basis': 'video_seconds', 'alignment': 'UNKNOWN', 'points': [], 'windows': [], 'telemetry_error': None}
    if not incident.get('telemetry_uri'):
        result['telemetry_error'] = 'Không có telemetry để vẽ biểu đồ.'
        return result
    try:
        log = normalize_log(_resolve_asset(incident_id, incident['telemetry_uri']))
        video = incident['video_metadata']
        anchors = [TimeAnchor(**point) for point in video.get('anchors', [])]
        offset = video.get('log_offset_s', get_settings().qwen_v1_log_offset_s)
        if log.config.timestamp_column != 't_video_s' and not anchors and offset is not None:
            anchors = [TimeAnchor(-offset, 0., 'configured_v1_log_offset'), TimeAnchor(video['duration'] - offset, video['duration'], 'configured_v1_log_offset')]
        mapping = align(video, log, anchors)
        result['alignment'] = mapping.quality
        if mapping.quality != 'VERIFIED':
            result['telemetry_error'] = 'Chưa xác minh đồng bộ CSV/video; không vẽ dữ liệu lên đồng hồ video.'
            return result
        windows = [check['window_s'] for check in checks if 'window_s' in check]
        if not windows:
            try:
                path = _resolve_asset(incident_id, f'{incident_id}/output/local-analysis.json')
                windows = json.loads(path.read_text()).get('visual_coverage', {}).get('candidate_windows', [])
            except (OSError, ValueError, ApiError):
                pass
        result['windows'] = windows
        if windows:
            start = max(0, min(w[0] for w in windows) - 1)
            end = min(video['duration'], max(w[1] for w in windows) + 1)
        else:
            start, end = 0, video['duration']
        rows = []
        for row in log.iter_rows():
            at = mapping.to_video_seconds(row['time_s'])
            if start <= at <= end:
                rows.append({**row, 'time_s': at})
        result['points'] = chart_points(rows)
    except (OSError, ValueError, KeyError, ApiError) as exc:
        result['telemetry_error'] = 'Không đọc được telemetry đồng bộ: ' + str(exc)
    return result
