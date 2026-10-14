/* Run: node frontend/tests/v2-polling-regression.cjs
 * Production TS modules executed with fake timers/hooks; not browser E2E.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const frontend = path.resolve(__dirname, '..');
function load(file, mocks = {}, globals = {}) {
  const exports = {};
  const code = ts.transpileModule(fs.readFileSync(path.join(frontend, file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX }, fileName: file }).outputText;
  vm.runInNewContext(code, { exports, require(name) { if (name in mocks) return mocks[name]; throw new Error('Unexpected dependency: ' + name); }, URL, Error, TypeError, AbortController, DOMException, ...globals }, { filename: file });
  return exports;
}
async function flush() { for (let i = 0; i < 20; i++) await Promise.resolve(); }
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
function clock() {
  let now = 0, next = 0; const timers = new Map();
  return { timers, get now() { return now; }, setTimeout(fn, delay) { const id = ++next; timers.set(id, { fn, at: now + delay, delay }); return id; }, clearTimeout(id) { timers.delete(id); }, async tick(ms) { const until = now + ms; for (;;) { const first = [...timers.entries()].filter(([, t]) => t.at <= until).sort((a, b) => a[1].at - b[1].at)[0]; if (!first) break; now = first[1].at; timers.delete(first[0]); first[1].fn(); await flush(); } now = until; await flush(); }, nextDelay() { return Math.min(...[...timers.values()].map(t => t.at - now)); } };
}
function hooks() {
  const slots = []; let cursor = 0, effects = [], alive = true, lateWrites = 0;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial; return [slots[i], value => { if (!alive) lateWrites++; slots[i] = typeof value === 'function' ? value(slots[i]) : value; }]; },
    useRef(initial) { const i = cursor++; if (!(i in slots)) slots[i] = { current: initial }; return slots[i]; },
    useCallback(fn, deps) { const i = cursor++, previous = slots[i]; if (!previous || deps.some((d, j) => d !== previous.deps[j])) slots[i] = { fn, deps }; return slots[i].fn; },
    useMemo(fn) { cursor++; return fn(); },
    useEffect(fn, deps) { const i = cursor++, previous = slots[i]; if (!previous || deps.some((d, j) => d !== previous.deps[j])) { const slot = { deps }; slots[i] = slot; effects.push(() => { previous?.cleanup?.(); slot.cleanup = fn(); }); } },
  };
  const jsx = (type, props) => ({ type, props: props || {} });
  return { react, runtime: { jsx, jsxs: jsx, Fragment: 'fragment' }, get lateWrites() { return lateWrites; }, render(component, props) { cursor = 0; effects = []; const tree = component(props); for (const effect of effects) effect(); return tree; }, unmount() { alive = false; for (const slot of slots) slot?.cleanup?.(); } };
}
function nodes(tree, predicate) { if (!tree || typeof tree !== 'object') return []; if (Array.isArray(tree)) return tree.flatMap(n => nodes(n, predicate)); return [...(predicate(tree) ? [tree] : []), ...nodes(tree.props?.children, predicate)]; }
function text(tree) { if (tree == null || typeof tree === 'boolean') return ''; if (Array.isArray(tree)) return tree.map(text).join(''); return typeof tree === 'object' ? text(tree.props?.children) : String(tree); }
function job(status) { return { job_id: 'J1', status, stage: 'PASS_1', progress: { done: 1, total: 4 }, budget: { calls_used: 0, max_calls: 20 }, partial_results: [], coverage: {}, error: null }; }

test('analysis progress ignores stale queued values and reserves completion for success', () => {
  const f = hooks();
  const { AnalysisProgress } = load('components/incidents/analysis-progress.tsx', { 'react/jsx-runtime': f.runtime, react: f.react }, { window: { matchMedia: () => ({ matches: true, addEventListener() {}, removeEventListener() {} }) } });
  for (const state of ['idle', 'queued']) {
    const tree = f.render(AnalysisProgress, { state, value: 25 });
    assert.equal(nodes(tree, node => node.props.role === 'progressbar')[0].props['aria-valuenow'], undefined);
    assert.ok(!text(tree).includes('25%'));
  }
  for (const [state, value, expected] of [['running', 100, 99], ['succeeded', null, 100], ['running', null, undefined]]) {
    const tree = f.render(AnalysisProgress, { state, value });
    assert.equal(nodes(tree, node => node.props.role === 'progressbar')[0].props['aria-valuenow'], expected);
  }
  for (const state of ['failed', 'cancelled']) assert.equal(f.render(AnalysisProgress, { state, value: 25 }).props['data-active'], false);
  assert.equal(f.render(AnalysisProgress, { state: 'running', value: 25, paused: true }).props['data-active'], false);
});

function pollerFixture(run, overrides = {}) {
  const time = clock(), errors = [];
  const { createSerialPoller } = load('lib/serial-poller.ts', {}, { setTimeout: time.setTimeout, clearTimeout: time.clearTimeout });
  return { time, errors, poller: createSerialPoller({ run, shouldRetry: () => true, onError: error => errors.push(error), intervalMs: 2000, maxRetryMs: 30000, ...overrides }) };
}
test('serial polling recovers after repeated errors and resets retry backoff on success', async () => {
  let attempts = 0;
  const f = pollerFixture(async () => { attempts++; if (attempts <= 3) throw new TypeError('offline'); return attempts === 4 ? 'active' : 'stop'; });
  await f.poller.refresh(); assert.equal(attempts, 1); assert.equal(f.time.nextDelay(), 2000);
  await f.time.tick(2000); assert.equal(attempts, 2); assert.equal(f.time.nextDelay(), 4000);
  await f.time.tick(4000); assert.equal(attempts, 3); assert.equal(f.time.nextDelay(), 8000);
  await f.time.tick(8000); assert.equal(attempts, 4); assert.equal(f.time.nextDelay(), 2000);
  await f.time.tick(2000); assert.equal(attempts, 5); assert.equal(f.time.timers.size, 0); assert.equal(f.errors.length, 3);
});
test('retry delays cap at configured maximum and permanent errors stop automatic polling', async () => {
  const f = pollerFixture(async () => { throw new Error('server unavailable'); }); await f.poller.refresh();
  for (const delay of [2000, 4000, 8000, 16000, 30000, 30000]) { assert.equal(f.time.nextDelay(), delay); await f.time.tick(delay); }
  f.poller.stop(); assert.equal(f.time.timers.size, 0);
  let calls = 0; const permanent = pollerFixture(async () => { calls++; throw new Error('forbidden'); }, { shouldRetry: () => false }); await permanent.poller.refresh(); await permanent.time.tick(100000); assert.equal(calls, 1); assert.equal(permanent.time.timers.size, 0);
});
test('slow in-flight requests deduplicate manual refreshes and no timer overlaps them', async () => {
  let calls = 0; const pending = deferred(); const f = pollerFixture(async () => { calls++; await pending.promise; return 'active'; });
  const one = f.poller.refresh(), two = f.poller.refresh(); await flush(); assert.equal(one, two); assert.equal(calls, 1); await f.time.tick(100000); assert.equal(calls, 1); assert.equal(f.time.timers.size, 0);
  pending.resolve(); await Promise.all([one, two]); assert.equal(f.time.nextDelay(), 2000); f.poller.stop();
});
test('manual refresh replaces a pending timer; suspend waits then resume starts one cycle', async () => {
  let calls = 0, pending; const f = pollerFixture(async () => { calls++; if (pending) await pending.promise; return 'active'; }); await f.poller.refresh(); assert.equal(f.time.timers.size, 1);
  await f.time.tick(1000); await f.poller.refresh(); assert.equal(calls, 2); assert.equal(f.time.nextDelay(), 2000);
  pending = deferred(); const refreshing = f.poller.refresh(); let suspended = false; const suspension = f.poller.suspend().then(() => { suspended = true; }); await flush(); assert.equal(suspended, false); await f.time.tick(50000); assert.equal(calls, 3);
  pending.resolve(); await refreshing; await suspension; assert.equal(suspended, true); assert.equal(f.time.timers.size, 0); await f.poller.refresh(); assert.equal(calls, 3);
  pending = null; await f.poller.resume(); assert.equal(calls, 4); assert.equal(f.time.timers.size, 1); f.poller.stop();
});
test('stop aborts in-flight signal and prevents late completion or manual refresh restarting', async () => {
  const pending = deferred(); let signal, calls = 0; const f = pollerFixture(async received => { calls++; signal = received; await pending.promise; return 'active'; }); const active = f.poller.refresh(); await flush(); assert.equal(signal.aborted, false); f.poller.stop(); assert.equal(signal.aborted, true);
  pending.resolve(); await active; await f.time.tick(100000); await f.poller.refresh(); assert.equal(calls, 1); assert.equal(f.time.timers.size, 0);
});
test('successful stop result schedules no timer and independent rebind owns its own signal', async () => {
  const oldPending = deferred(); let oldSignal; const old = pollerFixture(async signal => { oldSignal = signal; await oldPending.promise; return 'active'; }); const oldRequest = old.poller.refresh(); await flush(); old.poller.stop();
  let newSignal; const current = pollerFixture(async signal => { newSignal = signal; return 'stop'; }); await current.poller.refresh(); oldPending.resolve(); await oldRequest;
  assert.equal(oldSignal.aborted, true); assert.equal(newSignal.aborted, false); assert.equal(old.time.timers.size, 0); assert.equal(current.time.timers.size, 0);
});
function workspaceFixture() {
  const time = clock(), h = hooks(), requests = [], batches = [];
  const { createSerialPoller } = load('lib/serial-poller.ts', {}, { setTimeout: time.setTimeout, clearTimeout: time.clearTimeout });
  class ApiError extends Error { constructor(message, status) { super(message); this.status = status; } }
  const v2Request = (url, init = {}) => { const pending = deferred(); const req = { url, init, ...pending }; requests.push(req); return pending.promise; };
  const { RecordingWorkspace } = load('components/incidents/recording-workspace.tsx', { react: h.react, 'react/jsx-runtime': h.runtime, 'next/link': { default: 'Link' }, '@/components/ui/button': { Button: 'Button' }, '@/services/v2.service': { v2Request, v2Error: error => error.message }, '@/lib/api-client': { ApiError }, '@/lib/serial-poller': { createSerialPoller }, './analysis-progress': { AnalysisProgress: 'AnalysisProgress' } }, { crypto: { randomUUID: () => 'test-key' }, setTimeout: time.setTimeout, clearTimeout: time.clearTimeout });
  const render = (id = 'R1') => h.render(RecordingWorkspace, { id });
  const batch = () => { const group = requests.slice(batches.length * 3, batches.length * 3 + 3); assert.equal(group.length, 3); batches.push(group); return group; };
  const settle = async (group, status = 'running') => { for (const req of group) req.resolve(req.url.endsWith('/jobs') ? { items: status ? [job(status)] : [] } : req.url === '/session' ? { subject: 'engineer', roles: ['Engineer'] } : { items: [], next_cursor: null }); await flush(); };
  const refresh = tree => { const button = nodes(tree, n => n.type === 'Button' && ['Refresh', 'Retry'].includes(text(n)))[0]; assert.ok(button); button.props.onClick(); };
  return { time, h, requests, render, batch, settle, refresh, ApiError };
}

function incidentListFixture() {
  const h = hooks(), requests = [];
  const listIncidents = (limit, offset) => { const pending = deferred(); requests.push({ limit, offset, ...pending }); return pending.promise; };
  const { IncidentList } = load('components/incidents/incident-list.tsx', {
    react: h.react, 'react/jsx-runtime': h.runtime, 'next/link': { default: 'Link' },
    '@/components/auth/auth-provider': { useAuth: () => ({ status: 'authenticated', can: () => true }) },
    '@/components/icons': { ArrowRight: 'ArrowRight', FileText: 'FileText', Plus: 'Plus', Search: 'Search' },
    '@/services/incident-review.service': { loadIncidentReviews: async () => {} },
    '@/lib/format': { formatDate: () => 'date' }, '@/services/incident.service': { listIncidents },
    '@/components/ui/status-badge': { StatusBadge: 'StatusBadge' }, '@/components/ui/button': { Button: 'Button' },
  });
  return { h, requests, render: () => h.render(IncidentList, {}) };
}

function processingFixture(options = {}) {
  const h = hooks(), time = clock(), requests = { incident: [], jobs: [], reports: [], evidence: [], diagnostics: [] };
  let storedJobId = 'storedJobId' in options ? options.storedJobId : 'J1';
  const pendingRequest = (group, id) => { const pending = deferred(); requests[group].push({ id, ...pending }); return pending.promise; };
  let analysisStarts = 0;
  const { ProcessingView } = load('components/incidents/processing-view.tsx', {
    react: h.react, 'react/jsx-runtime': h.runtime, 'next/link': { default: 'Link' },
    '@/components/auth/auth-provider': { useAuth: () => ({ status: 'authenticated', can: () => options.canAnalyze !== false }) },
    '@/lib/api-client': { ApiError: class ApiError extends Error { constructor(message, status) { super(message); this.status = status; } }, isSessionReady: () => true, apiRequest: path => path.endsWith('/diagnostics') ? pendingRequest('diagnostics', path) : Promise.resolve({ job_id: null }) },
    '@/lib/config': { USE_MOCK_API: !options.realApi }, './pipeline-details': { PipelineDetails: 'PipelineDetails' },
    '@/components/icons': { ArrowLeft: 'ArrowLeft', ArrowRight: 'ArrowRight', Check: 'Check', CircleAlert: 'CircleAlert', Film: 'Film', Gauge: 'Gauge' },
    '@/components/ui/button': { Button: 'Button' }, './analysis-progress': { AnalysisProgress: 'AnalysisProgress' },
    '@/services/analysis.service': { analyzeIncident: async id => { analysisStarts++; storedJobId = 'J1'; return { job_id: 'J1', incident_id: id, status: 'queued' }; }, clearStoredJobId() { storedJobId = null; }, getAnalysisJob: id => pendingRequest('jobs', id), getStoredJobId: () => storedJobId },
    '@/services/evidence.service': { getEvidence: id => pendingRequest('evidence', id) },
    '@/services/incident.service': { getIncident: id => pendingRequest('incident', id) },
    '@/services/report.service': { getIncidentReport: id => pendingRequest('reports', id) },
  }, { setTimeout: time.setTimeout, clearTimeout: time.clearTimeout });
  return { h, time, requests, get analysisStarts() { return analysisStarts; }, render: id => h.render(ProcessingView, { id }) };
}

test('successful analysis remains terminal at 100%; retry reloads only failed report and opens review without rerunning analysis', async () => {
  const f = processingFixture();
  let tree = f.render('INC-1');
  f.requests.incident[0].resolve({ incident_id: 'INC-1', processing_status: 'PROCESSING', video_metadata: { width: 1920, height: 1080, duration: 12.5 } }); await flush();
  assert.equal(f.analysisStarts, 0); assert.equal(f.requests.jobs.length, 1);
  f.requests.jobs[0].resolve({ job_id: 'J1', status: 'succeeded', pass: 2, progress: { done: 10, total: 10 }, updated_at: 'now', result_uri: null, error: null }); await flush();
  assert.equal(f.requests.reports.length, 1); assert.equal(f.requests.evidence.length, 1);
  f.requests.reports[0].reject(new TypeError('offline')); f.requests.evidence[0].resolve([]); await flush(); tree = f.render('INC-1');
  assert.ok(nodes(tree, node => node.type === 'AnalysisProgress' && node.props.value === 100 && node.props.state === 'succeeded').length); assert.ok(text(tree).includes('Analysis completed, but some review data could not be loaded.')); assert.ok(!text(tree).includes('Draft report ready'));
  nodes(tree, node => node.type === 'Button' && text(node) === 'Retry failed loads')[0].props.onClick(); await flush();
  assert.equal(f.analysisStarts, 0, 'output retry must not start analysis'); assert.equal(f.requests.jobs.length, 1); assert.equal(f.requests.reports.length, 2); assert.equal(f.requests.evidence.length, 1, 'successful evidence response must be retained');
  f.requests.reports[1].resolve({ incident_id: 'INC-1' }); await flush(); tree = f.render('INC-1');
  assert.ok(text(tree).includes('Draft report ready')); assert.ok(nodes(tree, node => node.type === 'Link' && node.props.href === '/incidents/INC-1').length > 0); assert.ok(!text(tree).includes('offline')); f.h.unmount();
});

test('successful report is retained when evidence fails; retry recovers evidence without restarting analysis', async () => {
  const f = processingFixture();
  let tree = f.render('INC-2');
  f.requests.incident[0].resolve({ incident_id: 'INC-2', processing_status: 'PROCESSING', video_metadata: { width: 1280, height: 720, duration: 8 } }); await flush();
  f.requests.jobs[0].resolve({ job_id: 'J1', status: 'succeeded', pass: 2, progress: { done: 8, total: 8 }, updated_at: 'now', result_uri: null, error: null }); await flush();
  f.requests.reports[0].resolve({ incident_id: 'INC-2' }); f.requests.evidence[0].reject(new TypeError('evidence offline')); await flush(); tree = f.render('INC-2');
  assert.ok(text(tree).includes('Evidence: evidence offline'));
  nodes(tree, node => node.type === 'Button' && text(node) === 'Retry failed loads')[0].props.onClick(); await flush();
  assert.equal(f.analysisStarts, 0); assert.equal(f.requests.reports.length, 1, 'successful report must not be requested again'); assert.equal(f.requests.evidence.length, 2);
  f.requests.evidence[1].resolve([]); await flush(); tree = f.render('INC-2');
  assert.ok(text(tree).includes('Draft report ready')); assert.ok(nodes(tree, node => node.type === 'Link' && node.props.href === '/incidents/INC-2').length > 0); f.h.unmount();
});

test('opening a failed incident without a job never starts analysis; explicit retry deduplicates and respects permission', async () => {
  for (const canAnalyze of [true, false]) {
    const f = processingFixture({ storedJobId: null, canAnalyze }); f.render('I1');
    f.requests.incident[0].resolve({ incident_id: 'I1', processing_status: 'FAILED' }); await flush();
    const tree = f.render('I1'); assert.equal(f.analysisStarts, 0); assert.equal(f.time.timers.size, 0);
    const retry = nodes(tree, n => n.type === 'Button' && text(n) === 'Retry analysis');
    assert.equal(retry.length, canAnalyze ? 1 : 0);
    if (canAnalyze) { retry[0].props.onClick(); retry[0].props.onClick(); await flush(); assert.equal(f.analysisStarts, 1); assert.equal(f.requests.jobs.length, 1); }
    f.h.unmount();
  }
});

test('unknown running job uses GET incident status, stops at completion and never creates a job', async () => {
  const f = processingFixture({ storedJobId: null }); f.render('I1');
  f.requests.incident[0].resolve({ incident_id: 'I1', processing_status: 'PROCESSING' }); await flush();
  assert.equal(f.analysisStarts, 0); assert.equal(f.requests.jobs.length, 0);
  await f.time.tick(2000); assert.equal(f.requests.incident.length, 2);
  f.requests.incident[1].resolve({ incident_id: 'I1', processing_status: 'COMPLETED' }); await flush();
  f.requests.reports[0].resolve({}); f.requests.evidence[0].resolve([]); await flush();
  assert.equal(f.time.timers.size, 0); assert.equal(f.analysisStarts, 0); assert.ok(text(f.render('I1')).includes('Draft report ready')); f.h.unmount();
});

test('a stored job failing after a PROCESSING snapshot exposes explicit retry and clears its polling timer', async () => {
  const f = processingFixture(); f.render('I1'); f.requests.incident[0].resolve({ incident_id: 'I1', processing_status: 'PROCESSING' }); await flush();
  f.requests.jobs[0].resolve({ job_id: 'J1', status: 'failed', pass: 1, progress: { done: 1, total: 10 }, error: { message: 'failed' } }); await flush();
  assert.equal(f.time.timers.size, 0); assert.equal(f.analysisStarts, 0);
  assert.equal(nodes(f.render('I1'), n => n.type === 'Button' && text(n) === 'Retry analysis').length, 1); f.h.unmount();
});

function uploadFixture() {
  const h = hooks(), requests = [], cleared = [];
  let completed = 0;
  const uploadRecording = (file, recordingId, hash, onProgress, signal) => {
    const pending = deferred(); requests.push({ file, recordingId, hash, onProgress, signal, ...pending }); return pending.promise;
  };
  const { RecordingUpload } = load('components/incidents/recording-upload.tsx', {
    react: h.react, 'react/jsx-runtime': h.runtime, '@/components/ui/button': { Button: 'Button' },
    '@/services/v2.service': { uploadRecording, v2Error: error => error.message, clearUploadResume: id => cleared.push(id) },
  });
  return { h, requests, cleared, render: () => h.render(RecordingUpload, { onComplete: () => { completed++; } }), get completed() { return completed; } };
}

function uploadInputs(tree) { return nodes(tree, n => n.type === 'input'); }
test('upload service passes cancellation to init, part and complete requests and stops after abort', async () => {
  for (const stopAt of ['/uploads', '/uploads/U1/parts/1', '/uploads/U1/complete']) {
    const storage = new Map(), calls = [], controller = new AbortController();
    const stopped = deferred();
    class ApiError extends Error {}
    const { uploadRecording } = load('services/v2.service.ts', {
      '@/lib/api-client': { ApiError, parseApiError: async () => new Error('API failed') }, '@/lib/config': { API_BASE_URL: 'http://fixture/api/v1' },
    }, {
      process: { env: {} }, Headers, Blob, crypto: require('node:crypto').webcrypto,
      localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
      fetch: async (url, init) => {
        const endpoint = url.replace('http://fixture/api/v2', ''); calls.push({ endpoint, init });
        assert.equal(init.signal, controller.signal);
        if (endpoint === stopAt) { stopped.resolve(); await new Promise((_resolve, reject) => init.signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')), { once: true })); }
        return { ok: true, json: async () => endpoint === '/uploads' ? { upload_id: 'U1', parts: [], part_count: 1, part_size: 100 } : {} };
      },
    });
    const file = new Blob(['video'], { type: 'video/mp4' }); file.name = 'test.mp4';
    const run = uploadRecording(file, 'R1', 'a'.repeat(64), () => {}, controller.signal);
    const rejected = assert.rejects(run, cause => cause.name === 'AbortError');
    await stopped.promise; controller.abort(); await rejected;
    assert.equal(calls.at(-1).endpoint, stopAt); assert.ok(calls.every(call => call.init.signal.aborted));
  }
});

function setUploadFields(f, fileName = 'one.mp4') {
  let tree = f.render(), inputs = uploadInputs(tree);
  inputs[0].props.onChange({ target: { value: 'REC-1' } });
  tree = f.render(); inputs = uploadInputs(tree);
  const file = { name: fileName, size: 1234, lastModified: 1 };
  inputs[1].props.onChange({ target: { files: [file] } });
  tree = f.render(); inputs = uploadInputs(tree);
  inputs[2].props.onChange({ target: { value: 'a'.repeat(64) } });
  return { tree: f.render(), file };
}

test('upload cancel aborts request, suppresses stale completion and permits uploading the same displayed file again', async () => {
  const f = uploadFixture(); let { tree, file } = setUploadFields(f);
  let firstRun = nodes(tree, n => n.type === 'form')[0].props.onSubmit({ preventDefault() {} });
  assert.equal(f.requests[0].file, file); assert.equal(f.requests[0].recordingId, 'REC-1');
  tree = f.render(); nodes(tree, n => n.type === 'Button' && text(n) === 'Cancel upload')[0].props.onClick();
  assert.equal(f.requests[0].signal.aborted, true);
  tree = f.render(); assert.ok(text(tree).includes('Selected file: one.mp4')); assert.ok(!text(tree).includes('Uploading one.mp4'));

  const secondRun = nodes(tree, n => n.type === 'form')[0].props.onSubmit({ preventDefault() {} });
  assert.equal(f.requests[1].file, file); assert.equal(f.requests[1].signal.aborted, false);
  f.requests[0].resolve(); await firstRun; tree = f.render();
  assert.equal(f.completed, 0); assert.ok(text(tree).includes('Uploading one.mp4'));
  f.requests[1].resolve(); await secondRun; tree = f.render();
  assert.equal(f.completed, 1); assert.ok(!text(tree).includes('Uploading one.mp4')); f.h.unmount();
});

test('upload locks file selection/removal and duplicate submit until Cancel aborts; file can then change and upload again', async () => {
  const f = uploadFixture(); let { tree } = setUploadFields(f, 'old.mp4');
  const oldRun = nodes(tree, n => n.type === 'form')[0].props.onSubmit({ preventDefault() {} });
  tree = f.render(); let inputs = uploadInputs(tree); const newFile = { name: 'new.mp4', size: 4321, lastModified: 2 };
  assert.equal(inputs[1].props.disabled, true);
  assert.equal(nodes(tree, n => n.type === 'Button' && text(n) === 'Remove file')[0].props.disabled, true);
  inputs[1].props.onChange({ target: { files: [newFile] } });
  nodes(tree, n => n.type === 'Button' && text(n) === 'Remove file')[0].props.onClick();
  await nodes(tree, n => n.type === 'form')[0].props.onSubmit({ preventDefault() {} });
  tree = f.render(); assert.equal(f.requests.length, 1); assert.equal(f.requests[0].signal.aborted, false); assert.ok(text(tree).includes('Selected file: old.mp4'));
  nodes(tree, n => n.type === 'Button' && text(n) === 'Cancel upload')[0].props.onClick();
  tree = f.render(); inputs = uploadInputs(tree); assert.equal(inputs[1].props.disabled, false);
  inputs[1].props.onChange({ target: { files: [newFile] } });
  tree = f.render(); inputs = uploadInputs(tree);
  assert.equal(f.requests[0].signal.aborted, true); assert.ok(text(tree).includes('Selected file: new.mp4'));
  assert.equal(inputs[2].props.value, ''); assert.deepEqual(f.cleared, ['REC-1']);
  f.requests[0].resolve(); await oldRun; assert.equal(f.completed, 0);

  inputs[2].props.onChange({ target: { value: 'b'.repeat(64) } }); tree = f.render();
  const newRun = nodes(tree, n => n.type === 'form')[0].props.onSubmit({ preventDefault() {} });
  assert.equal(f.requests[1].file, newFile);
  tree = f.render(); const fileInput = uploadInputs(tree)[1]; fileInput.props.ref.current = { value: 'C:\\fakepath\\new.mp4' };
  nodes(tree, n => n.type === 'Button' && text(n) === 'Remove file')[0].props.onClick();
  tree = f.render(); assert.ok(text(tree).includes('Selected file: new.mp4')); assert.equal(f.requests[1].signal.aborted, false);
  nodes(tree, n => n.type === 'Button' && text(n) === 'Cancel upload')[0].props.onClick();
  tree = f.render(); nodes(tree, n => n.type === 'Button' && text(n) === 'Remove file')[0].props.onClick();
  tree = f.render(); assert.equal(f.requests[1].signal.aborted, true); assert.ok(!text(tree).includes('Selected file: new.mp4'));
  assert.equal(fileInput.props.ref.current.value, ''); assert.ok(nodes(tree, n => n.type === 'Button' && text(n) === 'Upload or resume')[0].props.disabled);
  f.requests[1].resolve(); await newRun; assert.equal(f.completed, 0);

  ({ tree } = setUploadFields(f, 'new.mp4'));
  const retryRun = nodes(tree, n => n.type === 'form')[0].props.onSubmit({ preventDefault() {} });
  assert.equal(f.requests[2].file.name, 'new.mp4'); f.requests[2].resolve(); await retryRun;
  assert.equal(f.completed, 1); f.h.unmount();
});

test('incident list separates initial error from empty, retries, clears recovered error and retains rows on refresh failure', async () => {
  const f = incidentListFixture();
  let tree = f.render(); assert.equal(f.requests.length, 1); assert.ok(!text(tree).includes('No incidents found'));
  f.requests[0].reject(new Error('initial service unavailable')); await flush(); tree = f.render();
  assert.ok(text(tree).includes('initial service unavailable')); assert.ok(!text(tree).includes('No incidents found'));
  nodes(tree, n => n.type === 'Button' && text(n) === 'Retry')[0].props.onClick(); tree = f.render(); assert.equal(f.requests.length, 2);

  const record = { incident_id: 'INC-1', processing_status: 'READY', created_at: '2026-10-11T00:00:00Z', incident_record: { scenario: 'stopped_vehicle' } };
  f.requests[1].resolve({ items: [record], total: 40, limit: 20, offset: 0 }); await flush(); tree = f.render();
  const incidentIds = () => nodes(tree, n => typeof n.type === 'function' && n.type.name === 'IncidentName').map(n => n.props.incident.incident_id);
  assert.ok(incidentIds().includes('INC-1')); assert.ok(!text(tree).includes('initial service unavailable'));

  nodes(tree, n => n.type === 'Button' && text(n) === 'Next')[0].props.onClick(); tree = f.render(); assert.equal(f.requests.length, 3);
  f.requests[2].reject(new Error('page refresh unavailable')); await flush(); tree = f.render();
  assert.ok(incidentIds().includes('INC-1')); assert.ok(text(tree).includes('page refresh unavailable')); assert.ok(!text(tree).includes('No incidents found'));
  nodes(tree, n => n.type === 'Button' && text(n) === 'Retry')[0].props.onClick(); tree = f.render(); assert.equal(f.requests.length, 4);
  f.requests[3].resolve({ items: [{ ...record, incident_id: 'INC-2' }], total: 40, limit: 20, offset: 20 }); await flush(); tree = f.render();
  assert.ok(incidentIds().includes('INC-2')); assert.ok(!text(tree).includes('page refresh unavailable')); f.h.unmount();
});
test('Load more preserves candidates on failure and clears only its old error after a successful retry', async () => {
  const f = workspaceFixture(); f.render(); await flush();
  const candidate = id => ({ candidate_id: id, recording_id: 'R1', window: { start_s: 1, critical_s: 2, end_s: 3 }, reasons: [id], analysis_state: 'PENDING', report_id: null });
  const group = f.batch(); group[0].resolve({ items: [candidate('A')], next_cursor: 'next' }); group[1].resolve({ items: [job('succeeded')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  let tree = f.render(); nodes(tree, n => n.type === 'Button' && text(n) === 'Load more candidates')[0].props.onClick(); await flush();
  f.requests[3].reject(new TypeError('old load-more error')); await flush(); tree = f.render(); assert.ok(text(tree).includes('old load-more error')); assert.ok(text(tree).includes('A'));
  nodes(tree, n => n.type === 'Button' && text(n) === 'Load more candidates')[0].props.onClick(); await flush();
  f.requests[4].resolve({ items: [candidate('A'), candidate('B')], next_cursor: null }); await flush(); tree = f.render();
  assert.ok(!text(tree).includes('old load-more error')); assert.equal(nodes(tree, n => n.type === 'li').length, 2); f.h.unmount();
});

test('workspace queued/running survives consecutive transient errors and restores status', async () => {
  const f = workspaceFixture(); f.render(); await flush(); await f.settle(f.batch(), 'queued'); let tree = f.render(); assert.ok(text(tree).includes('Analysis: queued'));
  for (let i = 0; i < 2; i++) { await f.time.tick(i === 0 ? 2000 : 4000); const batch = f.batch(); for (const request of batch) request.reject(new TypeError('offline')); await flush(); tree = f.render(); assert.ok(text(tree).includes('Analysis: queued')); }
  await f.time.tick(8000); await f.settle(f.batch(), 'running'); tree = f.render(); assert.ok(text(tree).includes('Analysis: running')); assert.ok(!text(tree).includes('offline')); assert.equal(f.time.nextDelay(), 2000); f.h.unmount();
});
test('workspace initial candidate failure shows error and Retry; recovered empty response clears error', async () => {
  const f = workspaceFixture(); f.render(); await flush(); let group = f.batch();
  group[0].reject(new TypeError('candidate service unavailable')); group[1].resolve({ items: [] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  let tree = f.render(); assert.ok(text(tree).includes('candidate service unavailable')); assert.ok(!text(tree).includes('No candidates have been recorded'));
  f.refresh(tree); await flush(); group = f.batch(); await f.settle(group, 'running'); tree = f.render();
  assert.ok(!text(tree).includes('candidate service unavailable')); assert.ok(text(tree).includes('No candidates have been recorded')); f.h.unmount();
});
test('workspace candidate refresh failure preserves existing records and recovered refresh clears error', async () => {
  const f = workspaceFixture(); f.render(); await flush(); let group = f.batch();
  const item = { candidate_id: 'C1', recording_id: 'R1', window: { start_s: 1, critical_s: 2, end_s: 3 }, reasons: ['retained candidate'], analysis_state: 'PENDING', report_id: null };
  group[0].resolve({ items: [item], next_cursor: null }); group[1].resolve({ items: [job('running')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  await f.time.tick(2000); group = f.batch(); group[0].reject(new TypeError('temporary candidate outage')); group[1].resolve({ items: [job('running')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  let tree = f.render(); assert.ok(text(tree).includes('retained candidate')); assert.ok(text(tree).includes('temporary candidate outage'));
  f.refresh(tree); await flush(); group = f.batch(); group[0].resolve({ items: [item] }); group[1].resolve({ items: [job('running')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  tree = f.render(); assert.ok(text(tree).includes('retained candidate')); assert.ok(!text(tree).includes('temporary candidate outage')); f.h.unmount();
});
test('workspace initial transient load retries and terminal/no-job snapshots stop', async () => {
  for (const status of ['succeeded', 'failed', 'cancelled', null]) {
    const f = workspaceFixture(); f.render(); await flush(); for (const request of f.batch()) request.reject(new TypeError('initial offline')); await flush(); assert.equal(f.time.nextDelay(), 2000);
    await f.time.tick(2000); await f.settle(f.batch(), status); f.render(); assert.equal(f.time.timers.size, 0); await f.time.tick(50000); assert.equal(f.requests.length, 6); f.h.unmount();
  }
});
test('workspace permanent API errors stop and manual refresh can explicitly recover', async () => {
  const f = workspaceFixture(); f.render(); await flush(); for (const request of f.batch()) request.reject(new f.ApiError('forbidden', 403)); await flush(); assert.equal(f.time.timers.size, 0); await f.time.tick(50000); assert.equal(f.requests.length, 3);
  f.refresh(f.render()); await flush(); await f.settle(f.batch(), 'running'); assert.ok(text(f.render()).includes('Analysis: running')); f.h.unmount();
});
test('workspace all requests carry a signal; failed sibling cannot cause overlap until batch settles', async () => {
  const f = workspaceFixture(); f.render(); await flush(); const first = f.batch(); assert.ok(first.every(r => r.init.signal instanceof AbortSignal)); assert.ok(first.every(r => r.init.signal === first[0].init.signal));
  first[0].reject(new TypeError('offline')); await flush(); f.refresh(f.render()); await f.time.tick(50000); assert.equal(f.requests.length, 3); assert.equal(f.time.timers.size, 0);
  first[1].resolve({ items: [job('running')] }); first[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush(); assert.equal(f.time.timers.size, 1); f.h.unmount(); assert.equal(f.time.timers.size, 0);
});
test('workspace unmount aborts pending requests and prevents subsequent state writes', async () => {
  const f = workspaceFixture(); f.render(); await flush(); const first = f.batch(); f.h.unmount(); assert.ok(first.every(r => r.init.signal.aborted)); await f.settle(first, 'running'); await f.time.tick(50000); assert.equal(f.h.lateWrites, 0); assert.equal(f.requests.length, 3); assert.equal(f.time.timers.size, 0);
});
test('workspace recording rebind aborts old batch and ignores old state completion', async () => {
  const f = workspaceFixture(); f.render('R1'); await flush(); const first = f.batch(); f.render('R2'); await flush(); const second = f.batch(); assert.ok(first.every(r => r.init.signal.aborted)); assert.ok(second.every(r => !r.init.signal.aborted));
  await f.settle(second, 'succeeded'); await f.settle(first, 'running'); const tree = f.render('R2'); assert.ok(text(tree).includes('Analysis: succeeded')); assert.ok(!text(tree).includes('Analysis: running')); assert.equal(f.time.timers.size, 0); f.h.unmount();
});
test('recording change hides old action errors immediately before the new load settles', async () => {
  const f = workspaceFixture(); f.render('R1'); await flush(); await f.settle(f.batch(), 'running');
  let tree = f.render('R1'); nodes(tree, n => n.type === 'Button' && text(n) === 'Cancel analysis')[0].props.onClick(); await flush();
  const action = f.requests[3]; assert.equal(action.init.method, 'POST'); action.reject(new Error('R1 action failed')); await flush();
  tree = f.render('R1'); assert.ok(text(tree).includes('R1 action failed'));
  tree = f.render('R2'); assert.ok(!text(tree).includes('R1 action failed')); assert.ok(!text(tree).includes('Analysis: running'));
  f.h.unmount();
});

test('polling merges candidates by ID, preserves loaded-page cursor and resets candidates on recording change', async () => {
  const f = workspaceFixture();
  const candidate = (id, reason) => ({ candidate_id: id, recording_id: 'R1', window: { start_s: 1, critical_s: 2, end_s: 3 }, reasons: [reason], analysis_state: 'PENDING', report_id: null });
  f.render('R1'); await flush();
  let group = f.batch();
  group[0].resolve({ items: [candidate('A', 'A original'), candidate('B', 'B original')], next_cursor: 'cursor-2' });
  group[1].resolve({ items: [job('running')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();

  let tree = f.render('R1'); nodes(tree, n => n.type === 'Button' && text(n) === 'Load more candidates')[0].props.onClick(); await flush();
  let more = f.requests[3]; assert.match(more.url, /cursor=cursor-2/);
  more.resolve({ items: [candidate('B', 'B updated'), candidate('C', 'C loaded')], next_cursor: 'cursor-3' }); await flush();

  await f.time.tick(2000); group = f.requests.slice(4, 7); assert.equal(group.length, 3);
  group[0].resolve({ items: [candidate('A', 'A updated'), candidate('D', 'D discovered')], next_cursor: 'cursor-2' });
  group[1].resolve({ items: [job('running')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  tree = f.render('R1');
  for (const label of ['A updated', 'B updated', 'C loaded', 'D discovered']) assert.ok(text(tree).includes(label), label);
  assert.equal(nodes(tree, n => n.type === 'li').length, 4);

  nodes(tree, n => n.type === 'Button' && text(n) === 'Load more candidates')[0].props.onClick(); await flush();
  more = f.requests[7]; assert.match(more.url, /cursor=cursor-3/, 'polling must preserve the cursor for the next loaded page');
  more.resolve({ items: [candidate('D', 'D updated'), candidate('E', 'E loaded')], next_cursor: null }); await flush();
  tree = f.render('R1');
  assert.equal(nodes(tree, n => n.type === 'li').length, 5); assert.equal((text(tree).match(/D updated/g) || []).length, 1);

  tree = f.render('R2');
  assert.ok(!text(tree).includes('A updated')); assert.ok(!text(tree).includes('Analysis: running')); assert.ok(text(tree).includes('Loading candidates and active job'));
  await flush();
  group = f.requests.slice(8, 11); assert.equal(group.length, 3);
  group[0].resolve({ items: [candidate('X', 'X recording two')], next_cursor: null });
  group[1].resolve({ items: [] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush();
  tree = f.render('R2');
  assert.ok(text(tree).includes('X recording two')); assert.ok(!text(tree).includes('A updated')); assert.ok(!text(tree).includes('C loaded')); assert.equal(nodes(tree, n => n.type === 'li').length, 1);
  f.h.unmount();
});

test('stop before scheduled microtask never starts a request', async () => {
  let calls = 0; const f = pollerFixture(async () => { calls++; return 'active'; }); const pending = f.poller.refresh(); f.poller.stop(); await pending; assert.equal(calls, 0); assert.equal(f.time.timers.size, 0);
});
test('delayed resume restores timer without immediate request and preserves terminal stop', async () => {
  let calls = 0; const f = pollerFixture(async () => { calls++; return calls === 1 ? 'active' : 'stop'; }); await f.poller.refresh(); await f.poller.suspend(); await f.poller.resume(false); assert.equal(calls, 1); assert.equal(f.time.nextDelay(), 2000); await f.time.tick(2000); assert.equal(calls, 2); await f.poller.suspend(); await f.poller.resume(false); assert.equal(f.time.timers.size, 0);
});
test('workspace HTTP timeout/rate-limit/server failures retry; auth/not-found errors stop', async () => {
  for (const status of [408, 429, 500, 503, 401, 403, 404]) {
    const f = workspaceFixture(); f.render(); await flush(); const group = f.batch(); group[0].reject(new f.ApiError('status ' + status, status)); group[1].resolve({ items: [job('running')] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush(); assert.equal(f.time.timers.size, status >= 500 || status === 408 || status === 429 ? 1 : 0, 'HTTP ' + status); f.h.unmount();
  }
});
test('permanent sibling error wins over transient error in a failed batch', async () => {
  const f = workspaceFixture(); f.render(); await flush(); const group = f.batch(); group[0].reject(new TypeError('offline')); group[1].reject(new f.ApiError('session expired', 401)); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush(); assert.equal(f.time.timers.size, 0); assert.ok(text(f.render()).includes('session expired')); f.h.unmount();
});
test('cancel action waits for existing poll, blocks read overlap and preserves mutation error after recovery', async () => {
  const f = workspaceFixture(); f.render(); await flush(); await f.settle(f.batch(), 'running'); let tree = f.render(); await f.time.tick(2000); const activeRead = f.batch();
  const cancel = nodes(tree, n => n.type === 'Button' && text(n) === 'Cancel analysis')[0]; assert.ok(cancel); cancel.props.onClick(); await flush(); f.refresh(f.render()); await f.time.tick(50000); assert.equal(f.requests.length, 6); assert.equal(f.time.timers.size, 0);
  await f.settle(activeRead, 'running'); await flush(); assert.equal(f.requests.length, 7); const action = f.requests[6]; assert.equal(action.init.method, 'POST'); assert.ok(action.init.signal instanceof AbortSignal); assert.equal(action.init.signal.aborted, false); f.refresh(f.render()); await f.time.tick(50000); assert.equal(f.requests.length, 7);
  action.reject(new Error('cancel denied')); await flush(); assert.equal(f.requests.length, 10); const recoveryRead = f.requests.slice(7); await f.settle(recoveryRead, 'running'); tree = f.render(); assert.ok(text(tree).includes('cancel denied')); assert.ok(text(tree).includes('Analysis: running')); assert.equal(f.time.nextDelay(), 2000); f.h.unmount();
});
test('unmount during mutation aborts operation and suppresses resumed reads or late writes', async () => {
  const f = workspaceFixture(); f.render(); await flush(); await f.settle(f.batch(), 'running'); const tree = f.render(); nodes(tree, n => n.type === 'Button' && text(n) === 'Cancel analysis')[0].props.onClick(); await flush(); const action = f.requests[3]; assert.equal(action.init.method, 'POST'); f.h.unmount(); assert.equal(action.init.signal.aborted, true); action.resolve({}); await flush(); await f.time.tick(50000); assert.equal(f.requests.length, 4); assert.equal(f.h.lateWrites, 0);
});

test('authoritative terminal job stops polling despite transient candidate failure', async () => {
  for (const status of ['succeeded', 'failed', 'cancelled']) {
    const f = workspaceFixture(); f.render(); await flush(); const group = f.batch(); group[0].reject(new TypeError('candidate offline')); group[1].resolve({ items: [job(status)] }); group[2].resolve({ subject: 'engineer', roles: ['Engineer'] }); await flush(); const tree = f.render(); assert.ok(text(tree).includes('Analysis: ' + status)); assert.ok(text(tree).includes('candidate offline')); assert.equal(f.time.timers.size, 0); await f.time.tick(50000); assert.equal(f.requests.length, 3); f.h.unmount();
  }
});
test('authoritative no-job response stops polling despite auxiliary session 503', async () => {
  const f = workspaceFixture(); f.render(); await flush(); const group = f.batch(); group[0].resolve({ items: [], next_cursor: null }); group[1].resolve({ items: [] }); group[2].reject(new f.ApiError('session unavailable', 503)); await flush(); const tree = f.render(); assert.ok(text(tree).includes('session unavailable')); assert.ok(text(tree).includes('No candidates have been recorded')); assert.equal(f.time.timers.size, 0); await f.time.tick(50000); assert.equal(f.requests.length, 3); f.h.unmount();
});

test('slow diagnostics do not block job status, completion or overlap requests', async () => {
  const f = processingFixture({ realApi: true }); f.render('INC-SLOW');
  f.requests.incident[0].resolve({ incident_id: 'INC-SLOW', processing_status: 'PROCESSING' }); await flush();
  f.requests.jobs[0].resolve({ job_id: 'J1', status: 'running', pass: 1, progress: { done: 4, total: 10 }, error: null }); await flush();
  assert.equal(f.requests.diagnostics.length, 1);
  let tree = f.render('INC-SLOW');
  assert.ok(nodes(tree, node => node.type === 'AnalysisProgress' && node.props.value === 20).length);
  await f.time.tick(2000); assert.equal(f.requests.jobs.length, 2);
  f.requests.jobs[1].resolve({ job_id: 'J1', status: 'succeeded', pass: 2, progress: { done: 10, total: 10 }, error: null }); await flush();
  assert.equal(f.requests.diagnostics.length, 1, 'only one diagnostics request may be in flight');
  f.requests.reports[0].resolve({ incident_id: 'INC-SLOW' }); f.requests.evidence[0].resolve([]); await flush();
  tree = f.render('INC-SLOW'); assert.ok(text(tree).includes('Draft report ready'));
  f.h.unmount(); f.requests.diagnostics[0].resolve({ state: 'late' }); await flush();
  assert.equal(f.h.lateWrites, 0);
});
