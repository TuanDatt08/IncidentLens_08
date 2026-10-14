// Service fixture tests, not browser/API E2E. Run from repository root.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const hash = 'b'.repeat(64), oldHash = 'a'.repeat(64);
const key = 'incidentlens:v2:upload:R1', meta = 'incidentlens:v2:upload-meta:R1';
function fixture(metadata, failComplete = false) {
  const storage = new Map([[key, 'OLD']]);
  if (metadata !== undefined) storage.set(meta, typeof metadata === 'string' ? metadata : JSON.stringify(metadata));
  const calls = [], exports = {};
  const upload = (id, resumed = false) => ({ upload_id: id, part_size: 2, part_count: 2, parts: resumed ? [{ number: 1 }, { number: 2 }] : id === 'OLD' ? [{ number: 1 }] : [] });
  class ApiError extends Error {}
  const code = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../services/v2.service.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  vm.runInNewContext(code, { exports, Error, DOMException, Headers, Blob, process: { env: {} }, crypto: require('node:crypto').webcrypto,
    require(name) { return name.includes('api-client') ? { ApiError, parseApiError: async () => new Error('complete failed') } : { API_BASE_URL: 'http://fixture/api/v1' }; },
    localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k) },
    fetch: async (url, init) => { const endpoint = url.replace('http://fixture/api/v2', ''); calls.push({ endpoint, init }); if (failComplete && endpoint.endsWith('/complete')) { failComplete = false; return { ok: false }; } return { ok: true, json: async () => endpoint === '/uploads' ? upload('NEW') : endpoint === '/uploads/OLD' ? upload('OLD') : endpoint === '/uploads/NEW' ? upload('NEW', true) : {} }; },
  });
  const file = new Blob(['abcd']); file.name = 'video.mp4';
  return { calls, storage, run: () => exports.uploadRecording(file, 'R1', hash, () => {}, new AbortController().signal) };
}
for (const [name, metadata] of [
  ['changed checksum', { upload_id: 'OLD', bytes: 4, sha256: oldHash }],
  ['missing metadata', undefined], ['corrupt metadata', '{broken'],
  ['different upload ID', { upload_id: 'OTHER', bytes: 4, sha256: hash }],
  ['changed size', { upload_id: 'OLD', bytes: 5, sha256: hash }],
]) test(`${name}: retry creates session with latest checksum`, async () => {
  const f = fixture(metadata); await f.run();
  const create = f.calls.find(c => c.endpoint === '/uploads' && c.init.method === 'POST');
  assert.ok(create, 'must not complete the old checksum session'); assert.equal(JSON.parse(create.init.body).sha256, hash);
  assert.ok(!f.calls.some(c => c.endpoint.startsWith('/uploads/OLD/')));
  assert.deepEqual(f.calls.filter(c => c.init.method === 'PUT').map(c => c.endpoint), ['/uploads/NEW/parts/1', '/uploads/NEW/parts/2']);
  assert.equal(f.storage.has(key), false); assert.equal(f.storage.has(meta), false);
});
test('same checksum and file resume verified parts after reload', async () => {
  const f = fixture({ upload_id: 'OLD', bytes: 4, sha256: hash }); await f.run();
  assert.ok(!f.calls.some(c => c.endpoint === '/uploads'));
  assert.deepEqual(f.calls.map(c => c.endpoint), ['/uploads/OLD', '/uploads/OLD/parts/2', '/uploads/OLD/complete']);
});
test('failed retry keeps updated session metadata for subsequent resume', async () => {
  const f = fixture({ upload_id: 'OLD', bytes: 4, sha256: oldHash }, true);
  await assert.rejects(f.run(), /complete failed/);
  assert.equal(f.storage.get(key), 'NEW'); assert.equal(JSON.parse(f.storage.get(meta)).sha256, hash);
  const count = f.calls.length; await f.run();
  assert.deepEqual(f.calls.slice(count).map(c => c.endpoint), ['/uploads/NEW', '/uploads/NEW/complete']);
  assert.equal(f.storage.has(key), false);
});
