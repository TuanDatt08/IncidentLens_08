// XHR service fixtures, not browser or backend integration.
const test = require('node:test'), assert = require('node:assert/strict');
const ts = require('typescript'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
function fixture(authEnabled = true) {
  const instances = [], events = [], exports = {};
  class XHR {
    constructor() { this.upload = {}; this.headers = {}; this.status = 201; this.responseText = '{"incident_id":"I1"}'; instances.push(this); }
    open(method, url) { this.method = method; this.url = url; }
    setRequestHeader(key, value) { this.headers[key] = value; }
    send(body) { this.body = body; }
    abort() { this.aborted = true; this.onabort?.(); }
  }
  const source = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../lib/api-client.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  vm.runInNewContext(source, { exports, require: () => ({ API_BASE_URL: '/api/v1', AUTH_ENABLED: authEnabled }), XMLHttpRequest: XHR, AbortController, DOMException, Headers, Response, FormData, Blob, Error, TypeError, Event, window: { dispatchEvent: event => events.push(event.type) } });
  return { api: exports, instances, events };
}
test('Qwen mode uploads without requiring a session or adding CSRF headers', async () => {
  const f = fixture(false);
  assert.equal(f.api.isSessionReady(), true);
  const body = new FormData(); body.append('sync_offset_s', '1.25');
  const pending = f.api.apiUpload('/incidents/upload', body);
  const xhr = f.instances[0];
  assert.equal(xhr.body.get('sync_offset_s'), '1.25');
  assert.equal(xhr.headers['X-CSRF-Token'], undefined);
  xhr.onload(); assert.equal((await pending).incident_id, 'I1');
});
test('real progress events, sent phase, CSRF and successful response are propagated without multipart header override', async () => {
  const f = fixture(); f.api.setSessionTransport('csrf'); const progress = [], body = new FormData(); let sent = false;
  const promise = f.api.apiUpload('/incidents/upload', body, { onProgress: (...args) => progress.push(args), onUploaded: () => sent = true });
  const xhr = f.instances[0]; assert.equal(xhr.body, body); assert.equal(xhr.headers['X-CSRF-Token'], 'csrf'); assert.equal(xhr.headers['Content-Type'], undefined);
  xhr.upload.onprogress({ loaded: 25, total: 100, lengthComputable: true }); assert.deepEqual(progress, [[25, 100]]); assert.equal(sent, false);
  xhr.upload.onprogress({ loaded: 30, lengthComputable: false }); assert.deepEqual(progress.at(-1), [30, undefined]);
  xhr.upload.onload(); assert.equal(sent, true); xhr.onload(); assert.equal((await promise).incident_id, 'I1'); assert.equal(xhr.onload, null);
});
test('cancel rejects even after upload body is sent, aborts XHR and suppresses stale callbacks', async () => {
  const f = fixture(); f.api.setSessionTransport('csrf'); const controller = new AbortController();
  const promise = f.api.apiUpload('/incidents/upload', new FormData(), { signal: controller.signal });
  const xhr = f.instances[0], late = xhr.onload; xhr.upload.onload(); controller.abort();
  await assert.rejects(promise, error => error.name === 'AbortError'); assert.equal(xhr.aborted, true); late(); assert.equal(xhr.upload.onprogress, null);
});
test('session change aborts pending upload; unauthenticated and already-aborted calls never send', async () => {
  const f = fixture(); await assert.rejects(f.api.apiUpload('/incidents/upload', new FormData()), error => error.status === 401); assert.equal(f.instances.length, 0);
  f.api.setSessionTransport('first'); const pending = f.api.apiUpload('/incidents/upload', new FormData()); f.api.setSessionTransport('second');
  await assert.rejects(pending, error => error.name === 'AbortError'); assert.equal(f.instances[0].aborted, true);
  const controller = new AbortController(); controller.abort(); await assert.rejects(f.api.apiUpload('/incidents/upload', new FormData(), { signal: controller.signal }), error => error.name === 'AbortError'); assert.equal(f.instances.at(-1).body, undefined);
});
test('API errors retain their code/status and session expiry dispatches the existing auth event', async () => {
  const f = fixture(); f.api.setSessionTransport('csrf');
  const pending = f.api.apiUpload('/incidents/upload', new FormData()); const xhr = f.instances[0]; xhr.status = 401; xhr.responseText = '{"error":{"code":"AUTHENTICATION_REQUIRED","message":"expired"}}'; xhr.onload();
  await assert.rejects(pending, error => error.status === 401 && error.code === 'AUTHENTICATION_REQUIRED'); assert.deepEqual(f.events, ['auth:expired']);
  const retry = f.api.apiUpload('/incidents/upload', new FormData()); f.instances[1].onerror(); await assert.rejects(retry, /network error/);
});
