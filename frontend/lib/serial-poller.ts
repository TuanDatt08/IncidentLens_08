type PollResult = "active" | "stop";
export type SerialPoller = { refresh: () => Promise<void>; suspend: () => Promise<void>; resume: (refreshNow?: boolean) => Promise<void>; stop: () => void };
type Options = { run: (signal: AbortSignal) => Promise<PollResult>; shouldRetry: (cause: unknown) => boolean; onError: (cause: unknown) => void; intervalMs?: number; maxRetryMs?: number };
export function createSerialPoller({ run, shouldRetry, onError, intervalMs = 2000, maxRetryMs = 30000 }: Options): SerialPoller {
  let stopped = false;
  let suspended = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | undefined;
  let pending: Promise<void> | undefined;
  let failures = 0;
  let nextDelay: number | undefined;
  function clearTimer() { if (timer !== undefined) clearTimeout(timer); timer = undefined; }
  function refresh(): Promise<void> {
    clearTimer();
    if (stopped || suspended) return pending ?? Promise.resolve();
    if (pending) return pending;
    const cycle = new AbortController();
    controller = cycle;
    pending = Promise.resolve().then(async () => {
      let delay: number | undefined;
      if (stopped || cycle.signal.aborted) { pending = undefined; controller = undefined; return; }
      try {
        const result = await run(cycle.signal);
        failures = 0;
        if (result === "active") delay = intervalMs;
      } catch (cause) {
        if (!stopped && !cycle.signal.aborted) {
          onError(cause);
          if (shouldRetry(cause)) { delay = Math.min(maxRetryMs, intervalMs * 2 ** Math.min(failures, 10)); failures += 1; }
        }
      } finally {
        pending = undefined; controller = undefined; nextDelay = delay;
        if (!stopped && !suspended && delay !== undefined) timer = setTimeout(() => { void refresh(); }, delay);
      }
    });
    return pending;
  }
  return {
    refresh,
    async suspend() { suspended = true; clearTimer(); await pending; },
    resume(refreshNow = true) {
      suspended = false;
      if (refreshNow) return refresh();
      if (!stopped && !pending && nextDelay !== undefined) {
        clearTimer();
        timer = setTimeout(() => { void refresh(); }, nextDelay);
      }
      return pending ?? Promise.resolve();
    },
    stop() { stopped = true; suspended = true; clearTimer(); controller?.abort(); },
  };
}
