import pytest

from backend.services.frame_clock import FrameClock


def test_video_only_coordinates_roundtrip_and_reject_invented_frame():
    clock = FrameClock([0., .25, .5, .75], 1.)
    original = {'time_basis': 'video_seconds', 'video_duration_s': 1.,
                'evidence': [{'evidence_id': 'F2', 'time_s': .25}],
                'timing': {'clip_start_s': 0., 'clip_end_s': 1., 'critical_s': None}}
    wire = clock.encode(original)
    assert wire['time_basis'] == 'frame_sequence'
    assert wire['total_frames'] == 4
    assert wire['evidence'][0]['frame_seq'] == 2
    assert 'time_s' not in wire['evidence'][0]
    assert clock.decode(wire) == original
    with pytest.raises(ValueError, match='frame'):
        clock.decode({'time_basis': 'video_seconds', 'time_s': .25})
    with pytest.raises(ValueError, match='frame'):
        clock.decode({'frame_seq': 2.5})
    with pytest.raises(ValueError, match='frame'):
        clock.decode({'frame_seq': 20})


def test_schema_and_prompt_use_frame_coordinates_without_seconds_contract():
    clock = FrameClock([0., .25], .5)
    schema = {'properties': {'time_s': {'type': 'number'}, 'time_basis': {'const': 'video_seconds'}},
              'required': ['time_s', 'time_basis']}
    transformed = clock.encode(schema)
    assert 'frame_seq' in transformed['properties']
    assert transformed['required'] == ['frame_seq', 'time_basis']
    assert transformed['properties']['time_basis']['const'] == 'frame_sequence'
    nullable = clock.encode({'critical_s': {'anyOf': [{'type': 'number'}, {'type': 'null'}]}})
    assert nullable['critical_frame_seq']['anyOf'][0] == {'type': 'integer', 'minimum': 1, 'maximum': 3}
