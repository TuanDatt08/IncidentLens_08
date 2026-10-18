"""Present telemetry analysis using the existing structured review sections."""
from backend.models.analysis_details import AnalysisDetails


def structured_telemetry_analysis(draft, *, details=None, candidate_id=None, telemetry_available=False, unresolved=False):
    sections = AnalysisDetails.model_validate(details or {}).model_dump(mode='json')
    sections['data_quality']['telemetry_available'] = telemetry_available
    if not telemetry_available:
        sections['data_quality']['time_sync_reliable'] = None
    sections['data_quality']['limitations'] = list(dict.fromkeys([
        *sections['data_quality']['limitations'], *draft.get('unknowns', []),
        'Chỉ quan sát các frame được cung cấp; không xác nhận độ phủ toàn video.',
    ]))
    if sections['event_details']['what_happened'] == 'UNKNOWN':
        sections['event_details']['what_happened'] = draft.get('summary') or 'UNKNOWN'
    if unresolved:
        sections['outcome']['collision_occurred'] = None
        sections['outcome']['near_miss_occurred'] = None
    return {
        **draft, **sections,
        'incident_id': candidate_id or 'TELEMETRY',
        'analysis_status': 'CONFIRMED' if draft.get('incident_detected') and not unresolved else 'INCONCLUSIVE',
        'timeline': [{**item, 'description': item.get('observation', item.get('description', ''))}
                     for item in draft.get('timeline', [])],
    }
