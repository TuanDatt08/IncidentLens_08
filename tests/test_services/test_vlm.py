from pathlib import Path

from src.models.contracts import AnalysisResult, LocalizationResult
from src.services.processing import PreparedPass2
from src.services.vlm import OpenAIVLMAdapter


class FakeStructuredModel:
    def __init__(self):
        self.calls = []

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        if self.schema is LocalizationResult:
            return LocalizationResult(incident_detected=False)
        return AnalysisResult(incident_detected=True, incident_window={"start": -1, "critical": 0, "end": 1})


def test_adapter_sends_frames_and_telemetry_without_storage_paths(tmp_path, monkeypatch):
    fake = FakeStructuredModel()
    monkeypatch.setattr("src.services.vlm.get_llm", lambda: fake)
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"jpeg")
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"mp4")
    adapter = OpenAIVLMAdapter()
    adapter.pass1(clip, [frame], {"duration": 5, "fps": 30})
    adapter.pass2(PreparedPass2("INC-001", clip, [frame], [{"sec_from_incident": -1.0}], -1, 0, 1))
    assert "data:image/jpeg;base64" in str(fake.calls[0])
    assert "sec_from_incident" in str(fake.calls[1])
    assert str(tmp_path) not in str(fake.calls)


def test_pass1_prompt_uses_actual_decodable_sample_times(tmp_path, monkeypatch):
    fake = FakeStructuredModel()
    monkeypatch.setattr("src.services.vlm.get_llm", lambda: fake)
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"jpeg")
    OpenAIVLMAdapter().pass1(tmp_path / "video.mp4", [frame] * 5, {"duration": 4.0, "fps": 10.0})
    prompt = str(fake.calls[0])
    assert "3.85" in prompt
    assert "3.99" not in prompt
