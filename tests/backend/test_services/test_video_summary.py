import pytest

from backend.services.video_summary import validate_summary


def summary(status='CONFIRMED', ids=None):
    return {'overall_status': status, 'summary': 'Có xung đột cần kiểm tra.',
            'events': [{'candidate_ids': ['C1'], 'status': 'CONFIRMED', 'event_type': 'OTHER',
                        'summary': 'Có xung đột.', 'evidence_ids': ids or ['F1', 'F2']}],
            'unknowns': [], 'review_status': 'DRAFT'}


def test_summary_rejects_new_evidence_and_unsupported_promotions():
    records = [{'candidate_id': 'C1', 'status': 'INCONCLUSIVE', 'evidence_ids': ['F1', 'F2']}]
    with pytest.raises(ValueError, match='evidence'):
        validate_summary(summary(ids=['MADE_UP']), records, {'F1', 'F2'}, [])
    with pytest.raises(ValueError, match='confirmed'):
        validate_summary(summary(), records, {'F1', 'F2'}, [])


def test_summary_preserves_unresolved_coverage_and_rejects_silent_omission():
    records = [{'candidate_id': 'C1', 'status': 'CONFIRMED', 'evidence_ids': ['F1', 'F2']}]
    result = validate_summary(summary(), records, {'F1', 'F2'}, ['Một chuỗi xử lý lỗi.'])
    assert result['overall_status'] == 'CONFIRMED'
    assert result['unknowns'] == ['Một chuỗi xử lý lỗi.']
    negative = summary('NO_INCIDENT_IN_OBSERVED_COVERAGE')
    negative['events'] = []
    with pytest.raises(ValueError, match='omitted'):
        validate_summary(negative, records, {'F1', 'F2'}, [])


def test_confirmed_event_cannot_borrow_only_negative_candidate_evidence():
    records = [{'candidate_id': 'C1', 'status': 'CONFIRMED', 'event_type': 'COLLISION', 'evidence_ids': ['CONTACT']},
               {'candidate_id': 'C2', 'status': 'NO_INCIDENT', 'evidence_ids': ['ORDINARY']}]
    data = summary(ids=['ORDINARY'])
    data['events'][0].update(candidate_ids=['C1', 'C2'], event_type='COLLISION')
    with pytest.raises(ValueError, match='confirmed'):
        validate_summary(data, records, {'CONTACT', 'ORDINARY'}, [])


def test_normal_sampling_limitations_do_not_require_logs_for_video_only_negative():
    data = summary('NO_INCIDENT_IN_OBSERVED_COVERAGE')
    data['events'] = []
    data['unknowns'] = ['Không có log; chỉ quan sát các frame lấy mẫu.']
    result = validate_summary(data, [{'candidate_id': 'C1', 'status': 'NO_INCIDENT', 'evidence_ids': []}], set(), [])
    assert result['overall_status'] == 'NO_INCIDENT_IN_OBSERVED_COVERAGE'


def test_model_omission_is_retained_as_unresolved_without_discarding_independent_positive():
    from backend.services.video_summary import preserve_summary_coverage

    records = [{'candidate_id': 'C1', 'status': 'CONFIRMED', 'event_type': 'OTHER', 'evidence_ids': ['F1', 'F2']},
               {'candidate_id': 'C2', 'status': 'INCONCLUSIVE', 'summary': 'Một nghi vấn khác.', 'evidence_ids': ['F3']}]
    completed = preserve_summary_coverage(summary(), records)
    assert completed['events'][1]['candidate_ids'] == ['C2']
    assert completed['events'][1]['status'] == 'INCONCLUSIVE'
    result = validate_summary(completed, records, {'F1', 'F2', 'F3'}, [])
    assert result['overall_status'] == 'CONFIRMED'
    assert any('SUMMARY_OMITTED_CANDIDATE' in item for item in result['unknowns'])


@pytest.mark.parametrize('repair_first', [False, True])
def test_hierarchical_summary_keeps_original_ids_and_journals_every_note(tmp_path, monkeypatch, repair_first):
    import json

    import httpx

    from backend.config import Settings
    from backend.services import video_summary
    from backend.services.evidence_extraction import EvidenceAsset

    frames = []
    for index in range(2):
        path = tmp_path / f'{index}.jpg'
        path.write_bytes(b'jpeg')
        frames.append(EvidenceAsset(f'F{index}', 'I', 'C', path, 'unused', index, index, 'VIDEO', 'image/jpeg', index))
    records = [{'candidate_id': f'C{index}', 'status': 'CONFIRMED' if index == 0 else 'NO_INCIDENT',
                'event_type': 'OTHER', 'summary': f'Quan sát chuỗi {index}.', 'evidence_ids': ['F0', 'F1'],
                'sequence_observations': [{'note': f'Ghi chú gốc {index}.'}]} for index in range(16)]
    requests = []
    original_client = httpx.Client
    def respond(request):
        context = json.loads(json.loads(request.content)['messages'][1]['content'][0]['text'])
        requests.append(context)
        confirmed = [record for record in context['records'] if record['status'] == 'CONFIRMED']
        result = {'overall_status': 'CONFIRMED' if confirmed else 'NO_INCIDENT_IN_OBSERVED_COVERAGE',
                  'summary': 'Đã tổng hợp các quan sát.', 'events': [], 'unknowns': [], 'review_status': 'DRAFT'}
        if confirmed:
            result['events'] = [{'candidate_ids': [record['candidate_id'] for record in confirmed],
                                 'status': 'CONFIRMED', 'event_type': 'OTHER', 'summary': 'Có xung đột.',
                                 'evidence_ids': ['F0', 'F1']}]
            if repair_first and len(requests) == 1:
                result['events'][0]['evidence_ids'] = ['MADE_UP']
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(result)}}]})
    monkeypatch.setattr(video_summary.httpx, 'Client', lambda **kwargs: original_client(transport=httpx.MockTransport(respond)))
    result = video_summary.summarize_video(records, evidence=frames, coverage={'sampled_entire_video': True},
            settings=Settings(_env_file=None), output=tmp_path, job_id='TEST')
    assert result['events'][0]['candidate_ids'] == ['C0']
    assert result['input_record_ids'] == [record['candidate_id'] for record in records]
    first_level_ids = {record['candidate_id'] for request in requests if request['decision_scope']=='SUMMARY_GROUP' for record in request['records']}
    assert first_level_ids == {f'C{index}' for index in range(16)}
    assert len(list((tmp_path / 'requests').glob('*.request.json'))) == (4 if repair_first else 3)
