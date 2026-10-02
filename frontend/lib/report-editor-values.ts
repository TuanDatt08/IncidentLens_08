export function parseEditorItems(value: string, original: unknown[]): unknown[] {
  const structured = original.some((item) => item !== null && typeof item === "object");
  return value.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    if (!structured) return line;
    let item: unknown;
    try { item = JSON.parse(line); }
    catch { throw new Error("Keep structured evidence items as valid JSON objects; their source, time and evidence must be preserved."); }
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      throw new Error("Each structured evidence item must remain an object.");
    }
    return item;
  });
}
