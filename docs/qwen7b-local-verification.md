# Qwen 7B local: installation and verification

Installed files under `backend/data/model`:
- `Qwen2.5-VL-7B-Instruct-Q8_0.gguf` (8,098,523,680 bytes)
- `mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf` (1,354,162,912 bytes)

Both SHA-256 hashes match the pinned ggml-org Hugging Face revision `508edd0afaa66bb9e9f40587acc2184f02daf1f6`. Source metadata and download records are in `backend/data/qwen7b-source.json` and `backend/data/qwen7b-install.json`.

Windows llama.cpp b11609 CPU and CUDA 12.4 archives were verified against GitHub release SHA-256 digests. Active runtime is `backend/data/runtime-win-cuda/llama-server.exe`. GTX 1650 4 GB uses 12 GPU layers, CPU projector, 16,384-token context, one slot. Initial startup and image inference are slow on this machine; cached calls are faster. No model was renamed or replaced with the existing 3B files.

Start local test services from repository root:

```powershell
./scripts/start-qwen7b-test.ps1
```

Frontend: http://localhost:3001/incidents
API: http://127.0.0.1:8001/health
Qwen: http://127.0.0.1:8091/health
Logs: `logs/runtime/qwen7b-test/`
Database: `backend/data/ui-test.db`, separate from the original PostgreSQL configuration.

Real checks:
- GGUF headers, source sizes and hashes passed; CUDA runtime executable runs.
- Vision inference on a generated black frame completed with a real local model response, not a mocked provider.
- Generated one-second black MP4 uploaded through the real API as `INC-71FDCC8743C5`.
- Latest job `JOB-8BB541764C5B` succeeded and report GET returned HTTP 200 with DRAFT/no detection.
- Full Python regression: 286 passed, 1 skipped. Ruff backend/API passed.

Integration repairs: deduplicate clamped scan timestamps for short/low-FPS video; apply the existing detection invariant grammar to self-hosted llama.cpp output. Strict backend validation remains enabled. This test does not establish real incident detection accuracy or validate login/RBAC. Unsynchronized telemetry still requires verified anchors or an explicitly established offset; no offset is inferred. The default editable Stage A/B prompt is not used by this single-stage GGUF test launcher; it selects the existing schema-compatible incident prompt.
