const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function config(env) {
  const exports = {};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/config.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, { exports, process: { env } });
  return exports;
}
test('default mock workspace does not require a real backend session', () => {
  assert.equal(config({}).USE_MOCK_API, true);
  assert.equal(config({}).AUTH_ENABLED, false);
});
test('real API defaults to same-origin authenticated transport', () => {
  const value = config({ NEXT_PUBLIC_USE_MOCK_API: 'false' });
  assert.equal(value.AUTH_ENABLED, true);
  assert.equal(value.API_BASE_URL, '/api/v1');
});
test('explicit legacy opt-out and explicit mock auth remain available', () => {
  assert.equal(config({ NEXT_PUBLIC_USE_MOCK_API: 'false', NEXT_PUBLIC_ENABLE_AUTH: 'false' }).AUTH_ENABLED, false);
  assert.equal(config({ NEXT_PUBLIC_ENABLE_AUTH: 'true' }).AUTH_ENABLED, true);
});
