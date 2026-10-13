from backend.services.review_context import chart_points


def test_chart_retains_braking_spike_and_units():
    rows = [{'time_s': float(i), 'speed': 10.0 if i < 500 else 0.0, 'brake': 1.0 if i == 499 else 0.0} for i in range(1000)]
    points = chart_points(rows)
    assert len(points) <= 600
    assert any(p['time_s'] == 499 and p['brake_pct'] == 100 for p in points)
    assert points[0]['speed_kmh'] == 36
    assert points[-1]['speed_kmh'] == 0
