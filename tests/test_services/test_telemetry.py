import pytest

from src.services.telemetry import TelemetryError, parse_telemetry, select_window


def test_canonical_timeline_preserves_negative_seconds_and_auxiliary_clocks(tmp_path):
    csv_path = tmp_path / "telemetry.csv"
    csv_path.write_text(
        "sec_from_incident,sim_time_s,wall_clock_ts,speed_kmh\n"
        "-2,100,2026-09-23T00:00:00Z,30\n"
        "-1,101,2026-09-23T00:00:01Z,20\n"
        "0,102,2026-09-23T00:00:02Z,5\n"
        "1,103,2026-09-23T00:00:03Z,0\n",
        encoding="utf-8",
    )
    metadata = parse_telemetry(csv_path)
    assert metadata.model_dump() == {
        "row_count": 4,
        "time_column": "sec_from_incident",
        "time_reference": "incident_relative",
        "start_s": -2.0,
        "end_s": 1.0,
    }
    rows = select_window(csv_path, -1, 0)
    assert [row["sec_from_incident"] for row in rows] == [-1.0, 0.0]
    assert rows[0]["sim_time_s"] == "101"
    assert rows[0]["wall_clock_ts"] == "2026-09-23T00:00:01Z"


@pytest.mark.parametrize(
    "content",
    [
        "sim_time_s\n1\n",
        "sec_from_incident\nNaN\n",
        "sec_from_incident\n0\n-1\n",
        "sec_from_incident\n",
    ],
)
def test_rejects_missing_invalid_or_unsorted_relative_clock(tmp_path, content):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(content, encoding="utf-8")
    with pytest.raises(TelemetryError):
        parse_telemetry(csv_path)
