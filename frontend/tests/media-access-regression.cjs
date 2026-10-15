const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function fixture(response) {
  const exports = {}, calls = [];
  const code = ts.transpileModule(fs.readFileSync('lib/media-access.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
  vm.runInNewContext(code, { exports, fetch: async (...args) => { calls.push(args); return { headers: { get: () => 'video/mp4' }, ...response, body: { cancel: async () => {} } }; } });
  return { exports, calls };
}
test('denied video is an access failure, not a codec failure', async () => {
  const f = fixture({ status: 403, ok: false });
  assert.match(await f.exports.mediaAccessFailure('/api/video'), /access|permission|sign in/i);
  assert.equal(f.calls[0][1].headers.Range, 'bytes=0-0');
});
test('successful media response leaves codec diagnosis to the player', async () => {
  const f = fixture({ status: 206, ok: true });
  assert.equal(await f.exports.mediaAccessFailure('/api/video'), null);
});
