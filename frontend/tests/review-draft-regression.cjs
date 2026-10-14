/* Run: node frontend/tests/review-draft-regression.cjs
 * Executes transpiled production modules with VM/browser/hook mocks; no DOM/E2E claims.
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
  const code = ts.transpileModule(fs.readFileSync(path.join(frontend, file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
    fileName: file,
  }).outputText;
  vm.runInNewContext(code, { exports, require(name) { if (name in mocks) return mocks[name]; throw new Error('Unexpected dependency: ' + name); }, URL, Error, ...globals }, { filename: file });
  return exports;
}
function recovery(storage = new Map(), now = 1700000000000) {
  const sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
  return { storage, api: load('lib/draft-recovery.ts', {}, { window: { sessionStorage }, Date: { now: () => now } }) };
}
const valid = value => !!value && typeof value.summary === 'string';
const key = 'incidentlens:report-draft:v1:U1:R1';
test('recovery round trip retains base version, fields and isolates keys', () => {
  const { api, storage } = recovery();
  assert.equal(api.writeDraftRecovery('v1:U1:R1', 3, { summary: 'unsaved', observations: 'evidence' }), true);
  assert.equal(api.readDraftRecovery('v1:U1:R1', valid).version, 3);
  assert.equal(api.readDraftRecovery('v1:U1:R1', valid).value.summary, 'unsaved');
  assert.equal(api.readDraftRecovery('v2:R1', valid), null);
  assert.equal(JSON.parse(storage.get(key)).schema, 1);
  assert.equal(api.clearDraftRecovery('v1:U1:R1'), true);
  assert.equal(api.readDraftRecovery('v1:U1:R1', valid), null);
});
test('recovery TTL boundary, expired and future timestamps', () => {
  const now = 1700000000000;
  const { api, storage } = recovery(new Map(), now);
  const put = savedAt => storage.set(key, JSON.stringify({ schema: 1, version: 2, savedAt, value: { summary: 'draft' } }));
  put(now - 86400000); assert.equal(api.readDraftRecovery('v1:U1:R1', valid).version, 2);
  put(now - 86400001); assert.equal(api.readDraftRecovery('v1:U1:R1', valid), null);
  put(now + 1); assert.equal(api.readDraftRecovery('v1:U1:R1', valid), null);
});
test('malformed, incompatible, invalid version and invalid field recovery is rejected', () => {
  const { api, storage } = recovery();
  for (const entry of ['broken json', 'null', '[]', JSON.stringify({ schema: 2, version: 1, savedAt: 1700000000000, value: { summary: 'x' } }), ...[-1, 1.5, '1', Number.MAX_SAFE_INTEGER + 1].map(version => JSON.stringify({ schema: 1, version, savedAt: 1700000000000, value: { summary: 'x' } })), JSON.stringify({ schema: 1, version: 1, savedAt: 'yesterday', value: { summary: 'x' } }), JSON.stringify({ schema: 1, version: 1, savedAt: 1700000000000, value: { summary: 123 } })]) {
    storage.set(key, entry); assert.equal(api.readDraftRecovery('v1:U1:R1', valid), null, entry);
  }
});
test('storage denied does not crash read/write/clear', () => {
  const window = {}; Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('denied'); } });
  const api = load('lib/draft-recovery.ts', {}, { window });
  assert.equal(api.readDraftRecovery('v1:U1:R1', valid), null);
  assert.equal(api.writeDraftRecovery('v1:U1:R1', 1, { summary: 'x' }), false);
  assert.equal(api.clearDraftRecovery('v1:U1:R1'), false);
});
function guard(dirty = true, working = false, answer = false) {
  let cleanup;
  const calls = { confirms: 0, alerts: 0, registrations: [], removals: [] };
  const listeners = {};
  class Element { closest() { return this.anchor || null; } }
  class HTMLAnchorElement extends Element {
    constructor(href, target = '', download = false) { super(); this.href = href; this.target = target; this.download = download; this.anchor = this; }
    hasAttribute(name) { return name === 'download' && this.download; }
  }
  const surface = name => ({ addEventListener(type, fn, capture) { listeners[name + ':' + type] = fn; calls.registrations.push([name, type, capture]); }, removeEventListener(type, fn, capture) { assert.equal(listeners[name + ':' + type], fn); delete listeners[name + ':' + type]; calls.removals.push([name, type, capture]); } });
  const window = { ...surface('window'), location: { href: 'http://localhost/reports/R1?mode=edit', origin: 'http://localhost', pathname: '/reports/R1', search: '?mode=edit' }, confirm() { calls.confirms++; return answer; }, alert() { calls.alerts++; } };
  const api = load('lib/use-unsaved-changes.ts', { react: { useEffect(fn) { cleanup = fn(); } } }, { window, document: surface('document'), Element, HTMLAnchorElement });
  api.useUnsavedChanges(dirty, working);
  function click(href = 'http://localhost/recordings', options = {}) {
    const event = { target: new HTMLAnchorElement(href, options.target, options.download), button: 0, defaultPrevented: false, prevented: false, stopped: false, immediate: false, preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; }, stopImmediatePropagation() { this.immediate = true; }, ...options };
    listeners['document:click']?.(event); return event;
  }
  return { calls, listeners, click, cleanup };
}
test('clean idle editor registers no navigation guard', () => {
  const g = guard(false, false); assert.equal(g.calls.registrations.length, 0); assert.equal(g.cleanup, undefined);
});
test('dirty editor cancellation intercepts same-tab navigation; confirmation allows it', () => {
  const cancel = guard(); const e = cancel.click(); assert.equal(e.prevented, true); assert.equal(e.stopped, true); assert.equal(e.immediate, true); assert.equal(cancel.calls.confirms, 1);
  const leave = guard(true, false, true); assert.equal(leave.click().prevented, false); assert.equal(leave.calls.confirms, 1);
});
test('new-tab, modifiers, download, hash-only, non-http and handled clicks remain available', () => {
  const g = guard();
  for (const options of [{ target: '_blank' }, { ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }, { defaultPrevented: true }, { download: true }]) assert.equal(g.click(undefined, options).prevented, false);
  assert.equal(g.click('http://localhost/reports/R1?mode=edit#timeline').prevented, false);
  assert.equal(g.click('mailto:test@example.test').prevented, false);
  assert.equal(g.click(undefined, { target: {} }).prevented, false);
  assert.equal(g.calls.confirms, 0);
});
test('working blocks navigation without discard confirmation and registers reload guard even when clean', () => {
  const g = guard(false, true, true); assert.equal(g.click().prevented, true); assert.equal(g.calls.confirms, 0); assert.equal(g.calls.alerts, 1);
  const event = { prevented: false, preventDefault() { this.prevented = true; } };
  g.listeners['window:beforeunload'](event); assert.equal(event.prevented, true); assert.equal(event.returnValue, '');
});
test('guard cleanup unregisters original handlers with matching capture', () => {
  const g = guard(); assert.equal(g.calls.registrations.length, 2); g.cleanup(); assert.deepEqual(g.calls.removals, g.calls.registrations); assert.equal(Object.keys(g.listeners).length, 0);
});
function hookHarness() {
  const slots = []; let cursor = 0; let effects = []; const cleanups = [];
  const react = { useCallback(fn, deps) { const i = cursor++; const previous = slots[i]; if (!previous || deps.some((d, j) => d !== previous.deps[j])) slots[i] = { fn, deps }; return slots[i].fn; }, useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial; return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; }]; }, useRef(initial) { const i = cursor++; if (!(i in slots)) slots[i] = { current: initial }; return slots[i]; }, useEffect(fn, deps) { const i = cursor++; const prev = slots[i]; if (!prev || deps.some((d, j) => d !== prev.deps[j])) { const slot = { deps }; slots[i] = slot; effects.push(() => { if (prev?.cleanup) prev.cleanup(); slot.cleanup = fn(); }); } } };
  const jsx = (type, props) => ({ type, props: props || {} });
  return { unmount() { for (const slot of slots) if (slot?.cleanup) slot.cleanup(); }, react, runtime: { jsx, jsxs: jsx, Fragment: 'fragment' }, render(component, props) { cursor = 0; effects = []; const tree = component(props); for (const effect of effects) { const cleanup = effect(); if (cleanup) cleanups.push(cleanup); } return tree; } };
}
function nodes(tree, predicate) {
  if (tree == null || typeof tree === 'boolean') return [];
  if (Array.isArray(tree)) return tree.flatMap(node => nodes(node, predicate));
  if (typeof tree !== 'object') return [];
  return [...(predicate(tree) ? [tree] : []), ...nodes(tree.props?.children, predicate)];
}
function text(tree) { if (tree == null || typeof tree === 'boolean') return ''; if (Array.isArray(tree)) return tree.map(text).join(''); if (typeof tree !== 'object') return String(tree); return text(tree.props?.children); }
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
function componentMocks(harness, service, extras = {}) {
  const icon = () => null;
  return { '@/components/auth/auth-provider': { useAuth: () => ({ user: { id: 'U1' }, can: () => true, status: 'authenticated' }) }, react: harness.react, 'react/jsx-runtime': harness.runtime, '@/components/icons': { Info: icon, Lock: icon, Save: icon, Check: icon, CircleAlert: icon, X: icon }, '@/components/ui/button': { Button: 'Button' }, '@/services/report.service': service, '@/lib/use-unsaved-changes': { useUnsavedChanges() {} }, ...extras };
}
test('editor locks slow-save inputs and preserves unsaved text and recovery on failure', async () => {
  const h = hookHarness(), request = deferred(), recoveries = new Map(); let calls = 0, saved = 0, cleared = 0;
  const service = { isEditableReviewState: () => true, ReportConflictError: class extends Error {}, updateReport: () => { calls++; return request.promise; } };
  const recovery = { readDraftRecovery: () => null, writeDraftRecovery: (key, version, value) => { recoveries.set(key, { version, value }); return true; }, clearDraftRecovery: () => { cleared++; return true; } };
  const { ReportEditor } = load('components/review/report-editor.tsx', componentMocks(h, service, { '@/lib/draft-recovery': recovery, '@/lib/use-unsaved-changes': { useUnsavedChanges() {} }, '@/lib/report-editor-values': { parseEditorItems: value => value.split('\n') } }));
  const props = { id: 'R1', draft: { version: 1, review_status: 'DRAFT', summary: 'original', observations: [], key_factors: [], unknowns: [] }, onSaved: () => saved++, onStateChange() {} };
  h.render(ReportEditor, props); let tree = h.render(ReportEditor, props);
  nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'my edit' } });
  tree = h.render(ReportEditor, props); const button = nodes(tree, n => n.type === 'Button' && text(n).includes('Save Changes'))[0];
  const pending = button.props.onClick(); button.props.onClick(); assert.equal(calls, 1);
  tree = h.render(ReportEditor, props); assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.disabled, true);
  assert.ok(nodes(tree, n => typeof n.type === 'function' && n.props.id).every(n => n.props.disabled));
  nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'lost edit' } });
  request.reject(new Error('network interrupted')); await pending;
  tree = h.render(ReportEditor, props); assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.value, 'my edit'); assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.disabled, false);
  assert.ok(text(tree).includes('network interrupted')); assert.equal(recoveries.get('v1:U1:R1').value.summary, 'my edit'); assert.equal(saved, 0); assert.equal(cleared, 0);
});
test('workflow dirty submit is disabled; pending transition cannot close or submit twice', async () => {
  const h = hookHarness(), request = deferred(); let calls = 0;
  const { WorkflowActions } = load('components/review/workflow-actions.tsx', componentMocks(h, { submitReport: () => { calls++; return request.promise; } }));
  const props = { id: 'R1', draft: { version: 1, review_status: 'DRAFT' }, onUpdated() {}, editorState: { dirty: true, saving: false } };
  let tree = h.render(WorkflowActions, props); assert.equal(nodes(tree, n => n.type === 'Button')[0].props.disabled, true);
  props.editorState = { dirty: false, saving: false }; tree = h.render(WorkflowActions, props); nodes(tree, n => n.type === 'Button')[0].props.onClick();
  tree = h.render(WorkflowActions, props); let dialog = nodes(tree, n => typeof n.type === 'function' && n.props.onConfirm)[0]; const pending = dialog.props.onConfirm(); dialog.props.onConfirm(); assert.equal(calls, 1); dialog.props.onClose();
  tree = h.render(WorkflowActions, props); dialog = nodes(tree, n => typeof n.type === 'function' && n.props.onConfirm)[0]; assert.ok(dialog); assert.equal(dialog.props.isWorking, true);
  const dh = hookHarness(); // Execute the actual dialog function with its parent's pending props.
  const dialogTree = dh.render(dialog.type, dialog.props);
  assert.ok(nodes(dialogTree, n => n.type === 'Button' || n.props['aria-label'] === 'Close dialog').every(n => n.props.disabled));
  let prevented = false; dialogTree.props.onCancel({ preventDefault() { prevented = true; } }); assert.equal(prevented, true);
  request.reject(new Error('submit failed')); await pending;
  tree = h.render(WorkflowActions, props); dialog = nodes(tree, n => typeof n.type === 'function' && n.props.onConfirm)[0]; assert.ok(dialog); assert.equal(dialog.props.isWorking, false); assert.equal(dialog.props.error, 'submit failed');
});

async function flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); }
function makeV2(storage = new Map(), options = {}) {
  const h = hookHarness();
  const recoveryApi = recovery(storage).api;
  const state = { actor: 'engineer-a', roles: ['Engineer'], failLoad: false, patch: null, transition: null, requests: [], report: { recording_id: 'recording-1', report_id: 'R1', version: 1, submitted_by: 'another-engineer', analysis: { review_status: 'DRAFT', summary: 'server summary', event_type: 'COLLISION', timeline: [{ time_s: 2.5, observation: 'server observation', certainty: 'OBSERVED', source: 'VIDEO', evidence_ids: ['E1'] }], factors: [{ label: 'server factor', category: 'EXTERNAL_CONDITION', claim_status: 'OBSERVED', evidence_ids: ['E1'] }], unknowns: ['unknown cause'] } }, ...options };
  const v2Request = async (url, init = {}) => {
    state.requests.push({ url, init });
    if (init.method === 'PATCH') return state.patch ? state.patch.promise : structuredClone(state.report);
    if (init.method === 'POST') return state.transition ? state.transition.promise : structuredClone(state.report);
    if (url === '/session') return { subject: state.actor, roles: state.roles };
    if (url.endsWith('/audit')) return { items: [], next_cursor: null };
    if (url.endsWith('/evidence')) return { items: [], next_cursor: null };
    if (state.failLoad) throw new Error('reload unavailable');
    return structuredClone(state.report);
  };
  const document = { activeElement: null };
  const module = load('components/review/report-workspace-v2.tsx', { react: h.react, 'react/jsx-runtime': h.runtime, 'next/link': { default: 'Link' }, '@/components/ui/button': { Button: 'Button' }, './audit-section': { AuditSection: 'AuditSection' }, './review-tabs': { ReviewTabs: 'ReviewTabs' }, './video-player': { VideoPlayer: 'VideoPlayer' }, './telemetry-panel': { TelemetryPanel: 'TelemetryPanel' }, './report-export': { ReportExport: 'ReportExport' }, '@/components/icons': { ArrowLeft: 'ArrowLeft' }, '@/components/ui/status-badge': { StatusBadge: 'StatusBadge' }, '@/services/v2.service': { V2_BASE_URL: '/api/v2', v2Request, v2Error: error => error.message }, '@/lib/draft-recovery': recoveryApi, '@/lib/use-unsaved-changes': { useUnsavedChanges() {} } }, { structuredClone, window: { confirm: () => true }, document });
  const render = () => h.render(module.ReportWorkspaceV2, { id: 'R1' });
  return { h, state, render, async mount() { render(); await flush(); return render(); } };
}
function buttonWith(tree, label) { const button = nodes(tree, n => n.type === 'Button' && text(n) === label)[0]; assert.ok(button, 'missing button ' + label); return button; }
function summaryOf(tree) { return nodes(tree, n => n.type === 'textarea' && n.props.rows === 4)[0]; }
test('V2 same actor/version restores all edited fields on remount and preserves typed metadata', async () => {
  const storage = new Map(), first = makeV2(storage); let tree = await first.mount();
  summaryOf(tree).props.onChange({ target: { value: 'recovered summary' } }); tree = first.render();
  nodes(tree, n => n.type === 'textarea' && n.props.rows === 2)[0].props.onChange({ target: { value: 'recovered observation' } }); tree = first.render();
  nodes(tree, n => n.type === 'input')[0].props.onChange({ target: { value: 'recovered factor' } }); first.h.unmount();
  const second = makeV2(storage); tree = await second.mount();
  assert.equal(summaryOf(tree).props.value, 'recovered summary');
  assert.equal(nodes(tree, n => n.type === 'textarea' && n.props.rows === 2)[0].props.value, 'recovered observation');
  assert.equal(nodes(tree, n => n.type === 'input')[0].props.value, 'recovered factor');
  assert.ok(text(tree).includes('Unsaved edits restored'));
  assert.ok(text(tree).includes('OBSERVED')); assert.ok(text(tree).includes('VIDEO')); assert.ok(text(tree).includes('E1'));
  assert.equal(buttonWith(tree, 'Submit for review').props.disabled, true);
});
test('V2 stale version is disclosed without automatic application and actor storage is isolated', async () => {
  const storage = new Map(), first = makeV2(storage); let tree = await first.mount(); summaryOf(tree).props.onChange({ target: { value: 'private draft' } }); first.h.unmount();
  const stale = makeV2(storage); stale.state.report.version = 2; tree = await stale.mount();
  assert.equal(summaryOf(tree).props.value, 'server summary'); assert.equal(summaryOf(tree).props.disabled, true); assert.ok(text(tree).includes('saved draft from version 1')); assert.ok(text(tree).includes('private draft'));
  const other = makeV2(storage, { actor: 'engineer-b' }); tree = await other.mount(); assert.equal(summaryOf(tree).props.value, 'server summary'); assert.ok(!text(tree).includes('private draft'));
});
test('V2 pending save locks fields and suppresses duplicates; failure retains edits and recovery', async () => {
  const storage = new Map(), workspace = makeV2(storage); let tree = await workspace.mount(); summaryOf(tree).props.onChange({ target: { value: 'keep my draft' } }); tree = workspace.render();
  const pending = deferred(); workspace.state.patch = pending; const save = buttonWith(tree, 'Save changes'); save.props.onClick(); save.props.onClick();
  tree = workspace.render(); assert.equal(workspace.state.requests.filter(r => r.init.method === 'PATCH').length, 1);
  assert.ok(nodes(tree, n => n.type === 'textarea' || n.type === 'input').every(n => n.props.disabled));
  summaryOf(tree).props.onChange({ target: { value: 'must not overwrite' } });
  pending.reject(new Error('save unavailable')); await flush(); tree = workspace.render();
  assert.equal(summaryOf(tree).props.value, 'keep my draft'); assert.equal(summaryOf(tree).props.disabled, false); assert.ok(text(tree).includes('save unavailable'));
  assert.equal(JSON.parse(storage.get('incidentlens:report-draft:v2:engineer-a:R1')).value.summary, 'keep my draft');
  const request = workspace.state.requests.find(r => r.init.method === 'PATCH'); const payload = JSON.parse(request.init.body);
  assert.equal(payload.timeline[0].certainty, 'OBSERVED'); assert.equal(payload.timeline[0].time_s, 2.5); assert.deepEqual(payload.timeline[0].evidence_ids, ['E1']); assert.equal(payload.factors[0].claim_status, 'OBSERVED');
});
test('V2 successful save clears recovery and later remount uses the saved server version', async () => {
  const storage = new Map(), workspace = makeV2(storage); let tree = await workspace.mount(); summaryOf(tree).props.onChange({ target: { value: 'saved summary' } }); tree = workspace.render();
  workspace.state.report.version = 2; workspace.state.report.analysis.summary = 'saved summary'; buttonWith(tree, 'Save changes').props.onClick(); await flush(); tree = workspace.render();
  assert.equal(storage.size, 0); assert.equal(summaryOf(tree).props.value, 'saved summary'); assert.equal(buttonWith(tree, 'Save changes').props.disabled, true); workspace.h.unmount();
  const next = makeV2(storage, { report: structuredClone(workspace.state.report) }); tree = await next.mount(); assert.equal(summaryOf(tree).props.value, 'saved summary'); assert.ok(!text(tree).includes('Unsaved edits restored'));
});
test('V2 failed reload retains visible draft and recovery for another remount', async () => {
  const storage = new Map(), workspace = makeV2(storage); let tree = await workspace.mount(); summaryOf(tree).props.onChange({ target: { value: 'retain on reload error' } }); tree = workspace.render(); workspace.state.failLoad = true;
  buttonWith(tree, 'Reload latest report').props.onClick(); await flush(); tree = workspace.render(); assert.equal(summaryOf(tree).props.value, 'retain on reload error'); assert.ok(text(tree).includes('reload unavailable')); assert.equal(storage.size, 1); workspace.h.unmount();
  tree = await makeV2(storage).mount(); assert.equal(summaryOf(tree).props.value, 'retain on reload error');
});
test('V2 reject request locks dialog controls, reason, Escape and duplicate confirms', async () => {
  const workspace = makeV2(); workspace.state.roles = ['Reviewer']; workspace.state.actor = 'reviewer'; workspace.state.report.analysis.review_status = 'IN_REVIEW'; let tree = await workspace.mount();
  buttonWith(tree, 'Reject report').props.onClick(); tree = workspace.render(); let dialog = nodes(tree, n => typeof n.type === 'function' && n.props.action === 'reject')[0]; dialog.props.setReason('needs correction'); tree = workspace.render(); dialog = nodes(tree, n => typeof n.type === 'function' && n.props.action === 'reject')[0];
  workspace.state.transition = deferred(); dialog.props.confirm(); dialog.props.confirm(); dialog.props.close(); tree = workspace.render(); dialog = nodes(tree, n => typeof n.type === 'function' && n.props.action === 'reject')[0]; assert.ok(dialog); assert.equal(dialog.props.busy, true); assert.equal(workspace.state.requests.filter(r => r.init.method === 'POST').length, 1);
  const dialogTree = workspace.h.render(dialog.type, dialog.props); assert.ok(nodes(dialogTree, n => n.type === 'Button' || n.type === 'textarea').every(n => n.props.disabled)); let prevented = false; dialogTree.props.onCancel({ preventDefault() { prevented = true; } }); assert.equal(prevented, true);
  workspace.state.transition.reject(new Error('reject unavailable')); await flush(); tree = workspace.render(); dialog = nodes(tree, n => typeof n.type === 'function' && n.props.action === 'reject')[0]; assert.equal(dialog.props.reason, 'needs correction'); assert.equal(dialog.props.error, 'reject unavailable');
});
test('V1 remount restores edit and successful save clears recovery', async () => {
  const storage = new Map(), recoveryApi = recovery(storage).api, draft = { version: 1, review_status: 'DRAFT', summary: 'server', observations: [], key_factors: [], unknowns: [] }; let latest = draft;
  function editor() {
    const h = hookHarness(); const props = { id: 'R1', draft: latest, onStateChange() {}, onSaved(updated) { latest = updated; props.draft = updated; } };
    const service = { isEditableReviewState: () => true, ReportConflictError: class extends Error {}, updateReport: async (id, patch) => ({ ...latest, ...patch, version: latest.version + 1 }), getIncidentReport: async () => latest };
    const { ReportEditor } = load('components/review/report-editor.tsx', componentMocks(h, service, { '@/lib/draft-recovery': recoveryApi, '@/lib/use-unsaved-changes': { useUnsavedChanges() {} }, '@/lib/report-editor-values': { parseEditorItems: value => value.split('\n') } }), { window: { confirm: () => true } });
    return { h, render: () => h.render(ReportEditor, props) };
  }
  let first = editor(); first.render(); let tree = first.render(); nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'restorable' } }); first.h.unmount();
  const second = editor(); second.render(); tree = second.render(); assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.value, 'restorable');
  await buttonWith(tree, 'Save Changes').props.onClick(); tree = second.render(); assert.equal(storage.size, 0); assert.equal(latest.summary, 'restorable'); assert.ok(text(tree).includes('Changes saved.')); second.h.unmount();
  const third = editor(); third.render(); tree = third.render(); assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.value, 'restorable'); assert.ok(!text(tree).includes('Unsaved edits restored'));
});

test('V1 conflict reload failure keeps recovery text; later successful reload discards confirmed edits', async () => {
  const h = hookHarness(), storage = new Map(), recoveryApi = recovery(storage).api; let fail = true;
  class ReportConflictError extends Error { constructor() { super('conflict'); this.currentVersion = 2; } }
  const props = { id: 'R1', draft: { version: 1, review_status: 'DRAFT', summary: 'server', observations: [], key_factors: [], unknowns: [] }, onStateChange() {}, onSaved(updated) { props.draft = updated; } };
  const service = { isEditableReviewState: () => true, ReportConflictError, updateReport: async () => { throw new ReportConflictError(); }, getIncidentReport: async () => { if (fail) throw new Error('reload unavailable'); return { ...props.draft, summary: 'new server', version: 2 }; } };
  const { ReportEditor } = load('components/review/report-editor.tsx', componentMocks(h, service, { '@/lib/draft-recovery': recoveryApi, '@/lib/use-unsaved-changes': { useUnsavedChanges() {} }, '@/lib/report-editor-values': { parseEditorItems: value => value.split('\n') } }), { window: { confirm: () => true } });
  const render = () => h.render(ReportEditor, props); render(); let tree = render(); nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'keep after conflict' } }); tree = render();
  await buttonWith(tree, 'Save Changes').props.onClick(); tree = render(); await buttonWith(tree, 'Reload latest report').props.onClick(); tree = render();
  assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.value, 'keep after conflict'); assert.ok(text(tree).includes('reload unavailable')); assert.equal(JSON.parse([...storage.values()][0]).value.summary, 'keep after conflict');
  fail = false; await buttonWith(tree, 'Reload latest report').props.onClick(); render(); tree = render(); assert.equal(storage.size, 0); assert.equal(nodes(tree, n => n.type === 'textarea')[0].props.value, 'new server');
});

function makeV1(storage = new Map(), options = {}) {
  const h = hookHarness(), recoveryApi = recovery(storage).api, updates = [];
  const state = { pending: null, states: [], draft: { version: 1, review_status: 'DRAFT', summary: 'server summary', observations: [], key_factors: [], unknowns: [] }, ...options };
  const props = { id: 'R1', draft: state.draft, onStateChange(value) { state.states.push(value); }, onSaved(value) { updates.push(value); props.draft = value; } };
  const { ReportEditor } = load('components/review/report-editor.tsx', componentMocks(h, { isEditableReviewState: status => status === 'DRAFT', ReportConflictError: class extends Error {}, updateReport: async () => state.pending ? state.pending.promise : props.draft }, { '@/lib/draft-recovery': recoveryApi, '@/lib/report-editor-values': { parseEditorItems: value => value.split('\n') } }), { window: { confirm: () => true } });
  return { h, state, updates, render: () => h.render(ReportEditor, props) };
}
test('V1 recovery hydration reports blocked state before allowing clean submission', () => {
  const editor = makeV1(); editor.render(); assert.equal(editor.state.states[0].dirty, true); editor.render(); assert.equal(editor.state.states.at(-1).dirty, false);
});
test('V1 readonly official text stays authoritative while recovery is available separately', () => {
  const storage = new Map(); recovery(storage).api.writeDraftRecovery('v1:U1:R1', 1, { summary: 'unsaved unofficial', observations: '', key_factors: '', unknowns: '' });
  const editor = makeV1(storage, { draft: { version: 1, review_status: 'APPROVED', summary: 'official approved', observations: [], key_factors: [], unknowns: [] } }); editor.render(); const tree = editor.render();
  assert.equal(nodes(tree, n => n.type === 'textarea' && n.props.id === 'summary')[0].props.value, 'official approved'); assert.equal(nodes(tree, n => n.type === 'textarea' && n.props.id === 'summary')[0].props.disabled, true); assert.ok(nodes(tree, n => n.type === 'textarea').some(n => n.props.value === 'unsaved unofficial')); assert.equal(storage.size, 1);
});
test('V1 and V2 reverting all fields to server values clears recovery', async () => {
  const v1Storage = new Map(), v1 = makeV1(v1Storage); v1.render(); let tree = v1.render(); nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'changed' } }); tree = v1.render(); assert.equal(v1Storage.size, 1);
  nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'server summary' } }); v1.render(); assert.equal(v1Storage.size, 0); assert.equal(v1.state.states.at(-1).dirty, false);
  const v2Storage = new Map(), v2 = makeV2(v2Storage); tree = await v2.mount(); summaryOf(tree).props.onChange({ target: { value: 'changed' } }); tree = v2.render(); assert.equal(v2Storage.size, 1); summaryOf(tree).props.onChange({ target: { value: 'server summary' } }); tree = v2.render(); assert.equal(v2Storage.size, 0); assert.equal(buttonWith(tree, 'Submit for review').props.disabled, false);
});
test('V1 unmounted slow save cannot erase a newer editor recovery or invoke onSaved', async () => {
  const storage = new Map(), old = makeV1(storage); old.render(); let tree = old.render(); nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'old submitted text' } }); tree = old.render(); old.state.pending = deferred(); const pending = buttonWith(tree, 'Save Changes').props.onClick(); old.h.unmount();
  const current = makeV1(storage); current.render(); tree = current.render(); nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'newer unsaved text' } });
  old.state.pending.resolve({ ...old.state.draft, version: 2, summary: 'old submitted text' }); await pending;
  assert.equal(JSON.parse([...storage.values()][0]).value.summary, 'newer unsaved text'); assert.equal(old.updates.length, 0);
});
test('V2 reload then unmount invalidates old PATCH before it can erase newer recovery', async () => {
  const storage = new Map(), old = makeV2(storage); let tree = await old.mount(); buttonWith(tree, 'Reload latest report').props.onClick(); await flush(); tree = old.render();
  summaryOf(tree).props.onChange({ target: { value: 'old pending edit' } }); tree = old.render(); old.state.patch = deferred(); buttonWith(tree, 'Save changes').props.onClick(); old.h.unmount();
  const current = makeV2(storage); tree = await current.mount(); summaryOf(tree).props.onChange({ target: { value: 'new lifetime edit' } });
  const before = storage.get('incidentlens:report-draft:v2:engineer-a:R1'); old.state.patch.resolve({ ...old.state.report, version: 2 }); await flush(); assert.equal(storage.get('incidentlens:report-draft:v2:engineer-a:R1'), before); assert.equal(JSON.parse(before).value.summary, 'new lifetime edit');
});

test('V2 readonly official analysis is unchanged while authorized saved edits remain separately viewable', async () => {
  const storage = new Map(); recovery(storage).api.writeDraftRecovery('v2:engineer-a:R1', 1, { summary: 'unofficial saved summary', timeline: ['unofficial saved observation'], factors: ['unofficial saved factor'] });
  const workspace = makeV2(storage); workspace.state.report.analysis.review_status = 'APPROVED'; const tree = await workspace.mount();
  assert.equal(summaryOf(tree).props.value, 'server summary'); assert.equal(summaryOf(tree).props.disabled, true);
  assert.equal(nodes(tree, n => n.type === 'textarea' && n.props.rows === 2)[0].props.value, 'server observation');
  assert.equal(nodes(tree, n => n.type === 'input')[0].props.value, 'server factor');
  assert.ok(text(tree).includes('View saved edits')); assert.ok(text(tree).includes('unofficial saved summary')); assert.ok(text(tree).includes('unofficial saved observation')); assert.equal(storage.size, 1);
});
test('V1 successful reload with denied removal warns and does not falsely erase recovery', async () => {
  const h = hookHarness(), storage = new Map(), recoveryApi = recovery(storage).api;
  const props = { id: 'R1', draft: { version: 1, review_status: 'DRAFT', summary: 'server', observations: [], key_factors: [], unknowns: [] }, onStateChange() {}, onSaved(updated) { props.draft = updated; } };
  class ReportConflictError extends Error {}
  const service = { isEditableReviewState: () => true, ReportConflictError, updateReport: async () => { throw new ReportConflictError('conflict'); }, getIncidentReport: async () => ({ ...props.draft, version: 2, summary: 'latest official' }) };
  const { ReportEditor } = load('components/review/report-editor.tsx', componentMocks(h, service, { '@/lib/draft-recovery': { ...recoveryApi, clearDraftRecovery: () => false }, '@/lib/report-editor-values': { parseEditorItems: value => value.split('\n') } }), { window: { confirm: () => true } });
  const render = () => h.render(ReportEditor, props); render(); let tree = render(); nodes(tree, n => n.type === 'textarea')[0].props.onChange({ target: { value: 'saved recovery remains' } }); tree = render(); await buttonWith(tree, 'Save Changes').props.onClick(); tree = render();
  await buttonWith(tree, 'Reload latest report').props.onClick(); render(); tree = render(); assert.equal(nodes(tree, n => n.type === 'textarea' && n.props.id === 'summary')[0].props.value, 'latest official'); assert.ok(text(tree).includes('could not remove its recovery copy')); assert.equal(JSON.parse([...storage.values()][0]).value.summary, 'saved recovery remains');
});
