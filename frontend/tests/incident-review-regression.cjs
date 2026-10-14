const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
class ApiError extends Error { constructor(status) { super('test error'); this.status = status; } }
function fixture(getIncidentReport) {
  const exports = {};
  const code = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../services/incident-review.service.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  vm.runInNewContext(code, { exports, require: name => name === '@/lib/api-client' ? { ApiError } : { getIncidentReport } });
  return exports.loadIncidentReviews;
}
const records = n => Array.from({ length: n }, (_, index) => ({ incident_id: String(index), processing_status: 'COMPLETED' }));
test('review reads cap concurrency at four, ignore unfinished processing and use report state', async () => {
  let active = 0, peak = 0;
  const seen = [];
  const load = fixture(async (id) => {
    active++; peak = Math.max(peak, active); await new Promise(resolve => setImmediate(resolve)); active--;
    return { review_status: id === '0' ? 'REJECTED' : 'DRAFT', version: 3 };
  });
  await load([...records(12), { incident_id: 'unfinished', processing_status: 'PROCESSING' }], new AbortController().signal, (id, result) => seen.push([id, result]));
  assert.equal(peak, 4); assert.equal(seen.length, 12);
  assert.equal(seen.find(([id]) => id === '0')[1].status, 'REJECTED');
  assert.equal(seen.every(([, result]) => result.version === 3), true);
});
test('missing, unauthorized and unknown states never become draft or approved', async () => {
  const seen = [];
  const load = fixture(async id => { if (id === '0') throw new ApiError(404); if (id === '1') return { review_status: 'UNKNOWN' }; throw new ApiError(401); });
  await load(records(8), new AbortController().signal, (id, result) => seen.push([id, result]));
  assert.equal(seen.find(([id]) => id === '0')[1].state, 'missing');
  assert.equal(seen.find(([id]) => id === '1')[1].state, 'error');
  assert.ok(seen.every(([, result]) => !result.status));
  let unauthorizedCalls = 0;
  await fixture(async () => { unauthorizedCalls++; throw new ApiError(401); })(records(8), new AbortController().signal, () => {});
  assert.ok(unauthorizedCalls <= 4);
});
test('aborted view receives no late review updates and starts no further reads', async () => {
  const controller = new AbortController(); let calls = 0; const seen = [];
  const load = fixture(async () => { calls++; controller.abort(); return { review_status: 'APPROVED', version: 1 }; });
  await load(records(8), controller.signal, (...args) => seen.push(args));
  assert.equal(calls, 1); assert.equal(seen.length, 0);
});
