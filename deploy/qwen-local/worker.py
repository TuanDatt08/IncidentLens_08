"""One consumer polls both queues sequentially to bound model memory."""
import logging
import sys
import time


def poll_once(v1, v2, *, ready=None):
    if ready is not None and not ready():
        return False
    first = v1()
    second = v2()
    return first or second


def main():
    sys.path.insert(0, "/app")
    from backend.config import get_settings
    from backend.services.qwen_local import create_local_provider, ensure_ollama_runtime
    from backend.worker import run_once as v1
    from backend.worker_v2 import run_once as v2
    settings = get_settings()
    provider = create_local_provider(settings.model_copy(update={"qwen_prompt_path": settings.qwen_log_prompt_path, "qwen_two_stage": False}))
    logging.basicConfig(level=logging.INFO)
    if settings.qwen_remote_ollama and settings.qwen_runtime != "ollama":
        raise ValueError("Remote inference mode requires Ollama")
    available = None

    def ready():
        nonlocal available
        try:
            ensure_ollama_runtime(settings)
            current = True
        except (ValueError, OSError):
            current = False
        if current != available:
            logging.info("Remote GPU %s; %s", "ready" if current else "unavailable", "processing queued jobs" if current else "jobs remain queued")
            available = current
        return current

    while True:
        if not poll_once(v1, lambda: v2(provider=provider), ready=ready if settings.qwen_remote_ollama else None):
            time.sleep(settings.worker_poll_s)


if __name__ == "__main__":
    main()
