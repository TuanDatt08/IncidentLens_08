/** Tab-scoped recovery for editor fields, never media or full reports. */
const PREFIX = "incidentlens:report-draft:";
const MAX_AGE_MS = 24 * 60 * 60 * 1000;

export type DraftRecovery<T> = { version: number; value: T };

export function readDraftRecovery<T>(key: string, validate: (value: unknown) => value is T): DraftRecovery<T> | null {
  try {
    const raw = window.sessionStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const entry: unknown = JSON.parse(raw);
    if (!entry || typeof entry !== "object") return null;
    const data = entry as Record<string, unknown>;
    if (data.schema !== 1 || typeof data.version !== "number" || !Number.isSafeInteger(data.version) || data.version < 0 || typeof data.savedAt !== "number" || !Number.isFinite(data.savedAt) || Date.now() - data.savedAt > MAX_AGE_MS || data.savedAt > Date.now() || !validate(data.value)) return null;
    return { version: data.version, value: data.value };
  } catch { return null; }
}

export function writeDraftRecovery<T>(key: string, version: number, value: T): boolean {
  try {
    window.sessionStorage.setItem(PREFIX + key, JSON.stringify({ schema: 1, version, savedAt: Date.now(), value }));
    return true;
  } catch { return false; }
}

export function clearDraftRecovery(key: string): boolean {
  try { window.sessionStorage.removeItem(PREFIX + key); return true; }
  catch { return false; }
}
