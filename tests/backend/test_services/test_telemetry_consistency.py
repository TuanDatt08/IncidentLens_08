from backend.services.telemetry_consistency import negative_telemetry_conflict


def test_negative_verdict_with_emergency_braking_requires_review():
    rows = [{'time_s': 57.375, 'speed': 8.875, 'brake': 0, 'acceleration': 0},
            {'time_s': 58.375, 'speed': 2.52, 'brake': .902, 'acceleration': -27.043},
            {'time_s': 58.625, 'speed': 0, 'brake': .902, 'acceleration': 0}]
    result = negative_telemetry_conflict(rows, 57.375, 59.125, False)
    assert result['code'] == 'MODEL_TELEMETRY_CONFLICT'
    assert result['requires_engineer_review'] is True
    assert result['speed_drop_m_s'] == 8.875
    assert negative_telemetry_conflict(rows, 53, 55, False) is None
    assert negative_telemetry_conflict(rows, 57.375, 59.125, True) is None


def test_ordinary_braking_does_not_override_negative_verdict():
    rows = [{'time_s': 0, 'speed': 8, 'brake': .9, 'acceleration': -1},
            {'time_s': 1, 'speed': 7, 'brake': .9, 'acceleration': -1}]
    assert negative_telemetry_conflict(rows, 0, 1, False) is None
