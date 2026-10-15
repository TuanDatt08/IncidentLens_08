"""Flag contradictory negative verdicts without inventing a visual incident."""


def braking_measurements(rows, start_s, end_s):
    selected = [row for row in rows if start_s <= row['time_s'] <= end_s]
    if len(selected) < 2:
        return None
    peak_brake = max(float(row.get('brake', 0)) for row in selected)
    deceleration = min(float(row.get('acceleration', 0)) for row in selected)
    speeds = [(float(row['time_s']), float(row['speed'])) for row in selected if 'speed' in row]
    # Only count forward speed loss over a short interval, not distant cruising changes.
    drop = max((before - after for t0, before in speeds for t1, after in speeds if 0 < t1 - t0 <= 2), default=0)
    if peak_brake < .8 or deceleration > -8 or drop < 3:
        return None
    return {'window_s': [start_s, end_s], 'peak_brake': peak_brake,
            'min_acceleration_m_s2': deceleration, 'speed_drop_m_s': drop,
            'speed_drop_max_interval_s': 2}


def negative_telemetry_conflict(rows, start_s, end_s, incident_detected):
    if incident_detected:
        return None
    measurements = braking_measurements(rows, start_s, end_s)
    if measurements is None:
        return None
    return {**measurements, 'code': 'MODEL_TELEMETRY_CONFLICT', 'requires_engineer_review': True,
            'message': 'Cần kỹ sư review: Qwen trả kết quả âm tính trong khi telemetry đồng bộ có phanh mạnh, giảm tốc lớn và tốc độ giảm nhanh. Chưa xác nhận near miss hoặc va chạm.'}
