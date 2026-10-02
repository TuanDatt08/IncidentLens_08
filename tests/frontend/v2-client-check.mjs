import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "../../frontend/node_modules/typescript/lib/typescript.js";

// Isolate the client with an in-memory transport; no browser credentials or network.
const source = (await readFile("frontend/services/v2.service.ts", "utf8")).replace(/^import .*;\r?$/gm, "");
const stubs = `const API_BASE_URL = 'http://fixture.invalid/api/v1';
class ApiError extends Error { constructor(message, status, code) { super(message); this.status = status; this.code = code; } }
async function parseApiError(response) { const body = await response.json(); return new ApiError(body.error.message, response.status, body.error.code); }
export { ApiError };`;
const output = ts.transpileModule(stubs + source, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ES2020 } }).outputText;
const client = await import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
assert.match(client.v2Error(new client.ApiError("denied", 403)), /role/);
assert.match(client.v2Error(new client.ApiError("stale", 409)), /edits have been kept/);
assert.match(client.v2Error(new client.ApiError("expired", 401)), /Sign in/);
const storage = new Map([["incidentlens:v2:upload:rec", "expired-fixture"]]);
globalThis.localStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) };
globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: "UPLOAD_EXPIRED", message: "expired" } }), { status: 409 });
await assert.rejects(client.uploadRecording({ name: "fixture.mp4", size: 0 }, "rec", "0".repeat(64), () => {}, new AbortController().signal), /start a new session/);
assert.equal(storage.size, 0);
const calls = [];
globalThis.fetch = async (url) => { calls.push(url); return new Response(JSON.stringify(url.endsWith("/uploads") ? { upload_id: "new-fixture", parts: [], part_count: 0 } : {})); };
await client.uploadRecording({ name: "fixture.mp4", size: 0 }, "rec", "0".repeat(64), () => {}, new AbortController().signal);
assert.equal(calls.length, 2);
assert.equal(storage.size, 0);
console.log("PASS: 401/403/409 copy, expired upload recovery, retry and completion cleanup");
