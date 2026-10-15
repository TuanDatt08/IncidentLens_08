import json

from backend.config import Settings
from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.services.qwen_processing import process_local_incident
from backend.services.video import VideoService
from backend.services.vlm_provider import ProviderResult


def run_candidate(tmp_path, monkeypatch, temporal, positive_first=False, invalid_final=False, video_summary=False):
    source = tmp_path/'INC-T/source'
    source.mkdir(parents=True)
    (source/'video.mp4').write_bytes(b'video')
    (source/'log.csv').write_text('t_video_s,brake,accel_x,speed_kmh\n'
        '0,0,0,36\n1,0,0,36\n2,.9,-27,25\n2.042,.9,-26,20\n2.083,.9,-25,15\n3,.9,0,0\n5,0,0,0\n')
    def extract(self, source, at, *args):
        path = args[-1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(str(at).encode())
        return path
    monkeypatch.setattr(VideoService,'extract_frame',extract)
    monkeypatch.setattr(VideoService,'extract_clip',extract)
    calls=[]
    class Provider:
        def analyze(self,context):
            calls.append(context)
            if invalid_final and context.candidate_observations:
                AIIncidentAnalysisV2.model_validate({'invalid':True})
            if positive_first and len(calls)==1:
                telemetry=next(a for a in context.registry.assets if a.source=='TELEMETRY')
                return ProviderResult(AIIncidentAnalysisV2.model_validate({
                    'schema_version':'2.0','incident_detected':True,'event_type':'HARD_BRAKING',
                    'time_basis':'video_seconds','window':{'start_s':1.,'critical_s':2.,'end_s':3.},
                    'summary':'Telemetry có phanh mạnh.', 'timeline':[{'time_s':2.,'observation':'Phanh mạnh.',
                    'evidence_ids':[telemetry.evidence_id],'source':'TELEMETRY','certainty':'OBSERVED'}],
                    'factors':[],'unknowns':[],'review_status':'DRAFT'}),{}, {})
            return ProviderResult(AIIncidentAnalysisV2.model_validate({
                'schema_version':'2.0','incident_detected':False,'event_type':'UNKNOWN',
                'time_basis':'video_seconds','window':None,'summary':'Không thấy va chạm.',
                'timeline':[],'factors':[],'unknowns':['Chưa rõ diễn biến.'],'review_status':'DRAFT'}),{}, {})
    settings=Settings(_env_file=None,qwen_flag_only=True,qwen_batch_frames=6 if temporal else 1,
                      qwen_temporal_context=temporal, qwen_video_summary=video_summary)
    incident={'incident_id':'INC-T','video_uri':'INC-T/source/video.mp4','telemetry_uri':'INC-T/source/log.csv',
              'video_metadata':{'duration':6.,'fps':24.}}
    result=process_local_incident(incident,storage_root=tmp_path,provider=Provider(),settings=settings)
    return result,calls,json.loads((tmp_path/'INC-T/local-analysis.json').read_text())


def test_single_frame_batches_cannot_hide_candidate_telemetry_conflict(tmp_path,monkeypatch):
    result,calls,manifest=run_candidate(tmp_path,monkeypatch,False)
    assert result.analysis.model_metadata['detection_state']=='REVIEW_REQUIRED_TELEMETRY_CONFLICT'
    assert len(result.analysis.model_metadata['consistency_checks'])==1
    assert len(result.analysis.model_metadata['draft_v2']['summary'].splitlines())==1
    assert len(result.analysis.model_metadata['draft_v2']['summary'])<700
    assert len(manifest['results'])>1


def test_final_verdict_does_not_or_preliminary_positives(tmp_path,monkeypatch):
    result,calls,manifest=run_candidate(tmp_path,monkeypatch,True,positive_first=True)
    assert not result.analysis.incident_detected
    assert any('MODEL_TEMPORAL_CONFLICT' in s for s in result.analysis.model_metadata['unknowns'])
    assert manifest['candidate_decisions'][0]['analyses'][0]['incident_detected'] is False


def test_invalid_final_is_not_accepted_as_an_uncontested_negative(tmp_path,monkeypatch):
    result,calls,manifest=run_candidate(tmp_path,monkeypatch,True,invalid_final=True)
    assert result.analysis.model_metadata['detection_state'].startswith('REVIEW_REQUIRED')
    assert manifest['candidate_decisions'][0]['analyses']==[]


def test_temporal_batches_overlap_and_final_decision_has_candidate_context(tmp_path,monkeypatch):
    result,calls,manifest=run_candidate(tmp_path,monkeypatch,True)
    assert all(2<=len(c.frames)<=6 for c in calls)
    assert calls[-1].candidate_observations
    assert not calls[0].candidate_observations
    assert {f.time_start_s for f in calls[0].frames}&{f.time_start_s for f in calls[1].frames}
    assert 2.0 in [f.time_start_s for f in calls[-1].frames]
    assert any(abs(f.time_start_s-2.125)<1e-6 for c in calls for f in c.frames)
    assert len(manifest['candidate_decisions'])==1
    assert result.analysis.model_metadata['detection_state']=='REVIEW_REQUIRED_TELEMETRY_CONFLICT'


def test_conflict_summary_preserves_independent_positive_finding():
    from types import SimpleNamespace

    from backend.services.qwen_processing import candidate_summary
    summary=candidate_summary(['Cũ.'],[SimpleNamespace(summary='Phanh khẩn cấp được xác nhận.')],
                              [{'message':'Candidate khác còn mâu thuẫn.'}])
    assert 'Phanh khẩn cấp được xác nhận.' in summary
    assert 'Candidate khác còn mâu thuẫn.' in summary


def test_log_pipeline_final_video_receives_all_sequence_notes_and_conflicts(tmp_path, monkeypatch):
    from backend.services import qwen_processing
    received = []
    def summarize(records, **kwargs):
        received.append((records, kwargs))
        return {'overall_status': 'INCONCLUSIVE', 'events': [], 'summary': 'Cần review do mâu thuẫn.',
                'unknowns': ['Mâu thuẫn telemetry.'], 'review_status': 'DRAFT'}
    monkeypatch.setattr(qwen_processing, 'summarize_video', summarize)
    result, calls, manifest = run_candidate(tmp_path, monkeypatch, True, video_summary=True)
    assert received
    records, kwargs = received[0]
    assert records[0]['sequence_observations']
    assert len(records[0]['sequence_observations']) == len(calls) - 1
    assert kwargs['coverage']['sampled_entire_video'] is False
    assert result.analysis.model_metadata['video_summary']['overall_status'] == 'INCONCLUSIVE'
    assert manifest['video_summary']['summary'] == 'Cần review do mâu thuẫn.'
