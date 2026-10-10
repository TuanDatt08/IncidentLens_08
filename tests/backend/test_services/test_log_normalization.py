import importlib

import pytest

from backend.services.telemetry import TelemetryError, parse_telemetry


def normalizer():
    return importlib.import_module("backend.services.log_normalization")


def test_legacy_csv_normalizes_without_reinterpreting_collision_clock(tmp_path):
    path = tmp_path / "telemetry.csv"
    path.write_text("sec_from_incident,speed\n-1,12\n0,11\n1,10\n", encoding="utf-8")
    assert parse_telemetry(path).start_s == -1
    result = normalizer().normalize_log(path, "csv")
    assert result.metadata.time_reference == "incident_relative"
    assert result.metadata.timestamp_unit == "s"
    assert list(result.iter_rows()) == [
        {"time_s": -1.0, "speed": "12"},
        {"time_s": 0.0, "speed": "11"},
        {"time_s": 1.0, "speed": "10"},
    ]


def test_epoch_nanoseconds_preserve_small_time_differences(tmp_path):
    path = tmp_path / "epoch.csv"
    path.write_text("clock_ns,speed\n1700000000000000000,12\n1700000000000000001,13\n", encoding="utf-8")
    module = normalizer()
    config = module.LogNormalizationConfig(timestamp_column="clock_ns", timestamp_unit="ns", time_reference="unix_epoch")
    result = module.normalize_log(path, "csv", config)
    assert result.metadata.time_reference == "recording_relative"
    assert result.metadata.source_time_reference == "unix_epoch"
    assert result.metadata.source_timestamp_origin == "1700000000000000000"
    assert [row["time_s"] for row in result.iter_rows()] == [0.0, 1e-9]
    assert result.metadata.row_count == 2


def test_recording_milliseconds_keep_declared_origin_and_units(tmp_path):
    path = tmp_path / "relative.csv"
    path.write_text("ms,mode\n1200,AUTO\n1800,MANUAL\n", encoding="utf-8")
    module = normalizer()
    config = module.LogNormalizationConfig(timestamp_column="ms", timestamp_unit="ms", time_reference="recording_relative")
    result = module.normalize_log(path, "csv", config)
    assert [row["time_s"] for row in result.iter_rows()] == [1.2, 1.8]
    assert result.metadata.start_s == 1.2
    assert result.metadata.end_s == 1.8


@pytest.mark.parametrize("csv", [
    "sec_from_incident\nNaN\n", "sec_from_incident\nInfinity\n",
    "sec_from_incident\n1\n1\n", "sec_from_incident\n2\n1\n",
    "sec_from_incident\ninvalid\n", "sec_from_incident\n",
    "other_clock\n1\n", "sec_from_incident,sec_from_incident\n0,0\n",
    "sec_from_incident,speed\n0,1,extra\n", "sec_from_incident,speed\n0\n",
])
def test_bad_csv_is_rejected_without_sorting_dropping_or_imputing(tmp_path, csv):
    path = tmp_path / "bad.csv"
    path.write_text(csv, encoding="utf-8")
    with pytest.raises(TelemetryError):
        normalizer().normalize_log(path, "csv")


@pytest.mark.parametrize("field,value", [("timestamp_unit", "minutes"), ("time_reference", "guess"), ("timestamp_column", "time_s")])
def test_ambiguous_or_unsupported_clock_configuration_is_rejected(field, value):
    with pytest.raises(TelemetryError):
        normalizer().LogNormalizationConfig(**{field: value})


def test_ros2_bag_is_explicitly_unsupported_before_reading(tmp_path):
    with pytest.raises(TelemetryError, match="ROS2 bag is not supported"):
        normalizer().normalize_log(tmp_path / "not-opened.db3", "ros2")


def test_iter_rows_stays_a_stream_instead_of_materializing_log(tmp_path):
    path = tmp_path / "large.csv"
    with path.open("w", encoding="utf-8") as stream:
        stream.write("sec_from_incident,speed\n")
        for i in range(10000):
            stream.write(f"{i},12\n")
    result = normalizer().normalize_log(path, "csv")
    rows = result.iter_rows()
    assert iter(rows) is rows
    assert next(rows) == {"time_s": 0.0, "speed": "12"}
    assert result.metadata.row_count == 10000
def test_carla_aliases_keep_source_columns_and_convert_speed_units(tmp_path):
    from backend.services.log_normalization import normalize_log
    path = tmp_path / "carla.csv"
    path.write_text("sec_from_incident,speed_kmh,accel_x,collision_intensity\n0,36,-2,0\n1,72,-3,5\n")
    log = normalize_log(path)
    rows = list(log.iter_rows())
    assert rows[0]["speed"] == 10.0 and rows[0]["acceleration"] == -2.0
    assert rows[0]["speed_kmh"] == "36"
    assert "acceleration" in log.metadata.signal_columns
