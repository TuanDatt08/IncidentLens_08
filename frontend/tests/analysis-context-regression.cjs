const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const jsx = (type, props) => ({ type, props });
function render(resource, mode) {
  const exports = {};
  const code = ts.transpileModule(fs.readFileSync('components/review/analysis-context.tsx', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  vm.runInNewContext(code, { exports, require(name) {
    if (name === 'react') return { createContext: () => ({}), useContext: () => resource, useEffect() {}, useState: x => [x, () => {}] };
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
    if (name.includes('config')) return { USE_MOCK_API: false, AUTH_ENABLED: false };
    return { default: 'Link', Button: 'Button' };
  } });
  return exports.AnalysisContext({ id: 'I1', mode, onSeek() {} });
}
test('shared failure is rendered once with an authentication recovery step', () => {
  const resource = { id: 'I1', error: 'Authentication required', accessError: true, retry() {} };
  const telemetry = render(resource, 'telemetry');
  assert.match(JSON.stringify(telemetry), /Workspace/);
  assert.match(JSON.stringify(telemetry), /alert/);
  assert.equal(render(resource, 'analysis'), null);
});
test('shared loading announces only one status', () => {
  const resource = { id: 'I1', error: '', retry() {} };
  assert.equal(render(resource, 'telemetry').props.role, 'status');
  assert.equal(render(resource, 'analysis'), null);
});
