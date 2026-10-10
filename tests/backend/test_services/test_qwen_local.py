import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest

from test_vlm_provider import context_and_config, provider_response


def test_local_prompt_reload_and_append_invalid_raw_output(tmp_path):
    module, context, config = context_and_config(tmp_path, "self_hosted")
    prompt = tmp_path / "promt.txt"
    outputs = tmp_path / "outputs.txt"
    prompt.write_text("Phân tích bằng chứng", encoding="utf-8")
    outputs.write_text("old history\n", encoding="utf-8")
    config = replace(config, prompt_path=str(prompt), outputs_path=str(outputs))
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=provider_response() if len(requests) == 1 else {"choices": [{"message": {"content": "invalid JSON"}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = module.create_provider(config, client=client)
        result = provider.analyze(context)
        assert result.provenance["prompt_sha256"]
        prompt.write_text("Prompt đã tối ưu", encoding="utf-8")
        with pytest.raises(ValueError):
            provider.analyze(context)
    assert "Phân tích" in requests[0]["messages"][0]["content"][0]["text"]
    assert "đã tối ưu" in requests[1]["messages"][0]["content"][0]["text"]
    history = outputs.read_text(encoding="utf-8")
    assert history.startswith("old history\n")
    records = [json.loads(line) for line in history.splitlines()[1:]]
    assert len(records) == 2 and records[1]["raw_output"] == "invalid JSON"
    assert records[0]["frame_times_s"] == [2.0]
    assert "base64" not in history and "gps" not in history


def test_missing_or_empty_prompt_blocks_request(tmp_path):
    module, context, config = context_and_config(tmp_path, "self_hosted")
    path = tmp_path / "missing.txt"
    config = replace(config, prompt_path=str(path), outputs_path=str(tmp_path / "outputs.txt"))
    with httpx.Client(transport=httpx.MockTransport(lambda request: pytest.fail("request with invalid prompt"))) as client:
        provider = module.create_provider(config, client=client)
        with pytest.raises(ValueError, match="prompt"):
            provider.analyze(context)
        path.write_text("  ", encoding="utf-8")
        with pytest.raises(ValueError, match="prompt"):
            provider.analyze(context)


def test_journal_concurrent_writers_preserve_every_entry(tmp_path):
    from backend.services.prompt_io import append_output
    path = tmp_path / "outputs.txt"
    path.write_text("history\n", encoding="utf-8")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: append_output(path, {"index": i, "raw_output": "tiếng Việt\nnext"}), range(24)))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "history"
    assert {json.loads(line)["index"] for line in lines[1:]} == set(range(24))


def test_output_write_failure_does_not_report_success(tmp_path):
    module, context, config = context_and_config(tmp_path, "self_hosted")
    prompt = tmp_path / "promt.txt"
    prompt.write_text("Analyze", encoding="utf-8")
    config = replace(config, prompt_path=str(prompt), outputs_path=str(tmp_path))
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response()))) as client:
        with pytest.raises(OSError):
            module.create_provider(config, client=client).analyze(context)


def test_local_factory_rejects_public_endpoint_without_network(monkeypatch):
    from backend.config import Settings
    from backend.services.qwen_local import create_local_provider
    settings = Settings(_env_file=None, qwen_endpoint="https://8.8.8.8/v1/chat/completions")
    with pytest.raises(ValueError, match="internal|loopback"):
        create_local_provider(settings)


def test_malformed_envelope_is_also_appended(tmp_path):
    module, context, config = context_and_config(tmp_path, "self_hosted")
    prompt = tmp_path / "promt.txt"
    prompt.write_text("Analyze", encoding="utf-8")
    outputs = tmp_path / "outputs.txt"
    config = replace(config, prompt_path=str(prompt), outputs_path=str(outputs))
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text="broken envelope"))) as client:
        with pytest.raises(ValueError):
            module.create_provider(config, client=client).analyze(context)
    assert "broken envelope" in outputs.read_text(encoding="utf-8")


def test_journal_writers_in_separate_processes(tmp_path):
    import subprocess
    import sys
    outputs = tmp_path / "outputs.txt"
    code = "from backend.services.prompt_io import append_output; import sys; [append_output(sys.argv[1], {'process':sys.argv[2], 'i':i}) for i in range(8)]"
    processes = [subprocess.Popen([sys.executable, "-c", code, str(outputs), str(i)]) for i in range(3)]
    assert all(process.wait(timeout=20) == 0 for process in processes)
    records = [json.loads(line) for line in outputs.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 24 and {(item["process"], item["i"]) for item in records} == {(str(p), i) for p in range(3) for i in range(8)}


def test_batch_cannot_cite_unseen_frames(tmp_path):
    module, context, config = context_and_config(tmp_path, "self_hosted")
    unseen = replace(context.frames[0], evidence_id="EVD-UNSEEN", time_start_s=4.0, time_end_s=4.0)
    context = replace(context, registry=replace(context.registry, assets=(*context.registry.assets, unseen)))
    response = provider_response()
    analysis = json.loads(response["choices"][0]["message"]["content"])
    analysis["window"] = {"start_s": 1.0, "critical_s": 4.0, "end_s": 5.0}
    analysis["timeline"][0].update(time_s=4.0, evidence_ids=["EVD-UNSEEN"])
    response["choices"][0]["message"]["content"] = json.dumps(analysis)
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response))) as client:
        with pytest.raises(ValueError):
            module.create_provider(config, client=client).analyze(context)


def test_runtime_startup_serializes_independent_processes(tmp_path):
    import subprocess
    import sys
    model = tmp_path / "model"
    model.mkdir()
    (model / "weights.gguf").write_bytes(b"GGUF-fixture")
    (model / "projector.gguf").write_bytes(b"GGUF-fixture")
    script = r'''
from pathlib import Path
import sys, threading
from unittest.mock import patch
from backend.config import Settings
from backend.services.qwen_local import ensure_qwen_runtime
root=Path(sys.argv[1])
class Response:
    def __init__(self, models):
        self.status_code=200 if (root/'ready').exists() else 503
    def json(self): return {'data':[{'id':'incidentlens-qwen-local'}]}
class Client:
    def __init__(self, **kw): pass
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def get(self,url): return Response(url.endswith('/models'))
class Process:
    def __init__(self,*args,**kw):
        with (root/'launches').open('a') as out: out.write('launch\n')
        self.state=None
        threading.Timer(0.4,lambda:(root/'ready').write_text('ready')).start()
    def poll(self): return self.state
    def terminate(self): self.state=0
    def kill(self): self.state=0
    def wait(self,**kw): return 0
s=Settings(_env_file=None,qwen_model_dir=str(root/'model'),qwen_model_file='weights.gguf',qwen_projector_file='projector.gguf',qwen_startup_timeout_s=5,qwen_outputs_path=str(root/'outputs.txt'))
with patch('backend.services.qwen_local.httpx.Client',Client),patch('backend.services.qwen_local.subprocess.Popen',Process),patch('backend.services.qwen_local.shutil.which',return_value='fake-server'):
    ensure_qwen_runtime(s)
'''
    processes = [subprocess.Popen([sys.executable, "-c", script, str(tmp_path)]) for _ in range(2)]
    assert all(process.wait(timeout=20) == 0 for process in processes)
    assert (tmp_path / "launches").read_text().splitlines() == ["launch"]


def test_runtime_lock_uses_writable_output_directory(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from backend.config import Settings
    from backend.services import qwen_local
    model = tmp_path / "model"
    model.mkdir()
    for name in ("model.gguf", "projector.gguf"):
        (model / name).write_bytes(b"GGUF-fixture")
    journal = tmp_path / "journal"
    journal.mkdir()
    paths = []
    @contextmanager
    def lock(path, timeout):
        paths.append(path)
        yield
    monkeypatch.setattr(qwen_local, "locked_file", lock)
    class Response:
        status_code = 200
        def json(self):
            return {"data": [{"id": "incidentlens-qwen-local"}]}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url): return Response()
    monkeypatch.setattr(qwen_local.httpx, "Client", Client)
    settings = Settings(_env_file=None, qwen_model_dir=str(model), qwen_model_file="model.gguf", qwen_projector_file="projector.gguf", qwen_outputs_path=str(journal / "outputs.txt"))
    qwen_local.ensure_qwen_runtime(settings)
    assert paths == [journal / "qwen-runtime.lock"]
