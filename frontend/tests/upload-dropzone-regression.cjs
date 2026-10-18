/* Run: node frontend/tests/upload-dropzone-regression.cjs
 * React hook/JSX harness for upload interactions; this is not browser E2E.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const frontend = path.resolve(__dirname, '..');

function harness(file, mocks) {
  const instances = new Map(); const effects = []; let current; let hookIndex;
  const react = {
    useState(initial) { const instance = current; const i = hookIndex++; if (!(i in instance.hooks)) instance.hooks[i] = typeof initial === 'function' ? initial() : initial; return [instance.hooks[i], value => { instance.hooks[i] = typeof value === 'function' ? value(instance.hooks[i]) : value; }]; },
    useRef(initial) { const instance = current; const i = hookIndex++; if (!(i in instance.hooks)) instance.hooks[i] = { current: initial }; return instance.hooks[i]; },
    useEffect(fn, deps) { const instance = current, i = hookIndex++, previous = instance.hooks[i]; if (!previous || deps.some((value, index) => value !== previous.deps[index])) { const next = { deps }; instance.hooks[i] = next; effects.push(() => { previous?.cleanup?.(); next.cleanup = fn(); }); } },
  };
  mocks.react = react;
  mocks['@/components/ui/page-header'] = { PageHeader: 'header' };
  mocks['@/components/auth/auth-provider'] = { useAuth: () => ({ can: () => true }) };
  const exports = {};
  const code = ts.transpileModule(fs.readFileSync(path.join(frontend, file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX }, fileName: file }).outputText;
  vm.runInNewContext(code, { exports, require(name) { if (name in mocks) return mocks[name]; throw new Error('Unexpected dependency: ' + name); }, Error, Promise, AbortController, DOMException }, { filename: file });
  function jsx(type, props) { return { type, props: props || {} }; }
  function expand(node, key) {
    if (node == null || typeof node === 'boolean' || typeof node === 'string' || typeof node === 'number') return node;
    if (Array.isArray(node)) return node.map((item, i) => expand(item, `${key}.${i}`));
    if (typeof node.type === 'function') {
      const id = `${key}:${node.type.name}`;
      if (!instances.has(id)) instances.set(id, { hooks: [] });
      const previous = current; const previousIndex = hookIndex; current = instances.get(id); hookIndex = 0;
      const result = node.type(node.props);
      current = previous; hookIndex = previousIndex;
      return expand(result, `${id}.render`);
    }
    return { ...node, props: { ...node.props, children: expand(node.props.children, `${key}.children`) } };
  }
  function render() {
    const id = `root:${exports[Object.keys(exports)[0]].name}`;
    if (!instances.has(id)) instances.set(id, { hooks: [] });
    const previous = current; const previousIndex = hookIndex; current = instances.get(id); hookIndex = 0;
    const result = exports[Object.keys(exports)[0]]();
    current = previous; hookIndex = previousIndex;
    const tree = expand(result, id);
    while (effects.length) effects.shift()();
    return tree;
  }
  return { render, unmount() { for (const instance of instances.values()) for (const hook of instance.hooks) hook?.cleanup?.(); } };
}
function nodes(tree, predicate) { if (!tree || typeof tree !== 'object') return []; if (Array.isArray(tree)) return tree.flatMap(item => nodes(item, predicate)); return [...(predicate(tree) ? [tree] : []), ...nodes(tree.props?.children, predicate)]; }

test('video drop and picker share validation; invalid replacement preserves file and announces error', () => {
  const mocks = {
    react: {},
    'react/jsx-runtime': { jsx: (type, props) => ({ type, props: props || {} }), jsxs: (type, props) => ({ type, props: props || {} }), Fragment: 'fragment' },
    'next/link': { default: 'a' }, 'next/navigation': { useRouter: () => ({ push() {} }) },
    '@/components/icons': new Proxy({}, { get: (_target, key) => String(key) }),
    '@/components/ui/button': { Button: 'button' }, '@/lib/format': { formatFileSize: size => `${size} bytes` },
    '@/services/incident.service': { uploadIncident: async () => ({ incident_id: 'R1' }) },
  };
  const h = harness('components/incidents/upload-form.tsx', mocks);
  const tree = h.render();
  const videoButton = nodes(tree, node => node.type === 'button' && node.props['aria-label'] === 'Choose Video file')[0];
  const input = nodes(tree, node => node.type === 'input' && node.props.id === 'incident-video')[0];
  assert.ok(videoButton); assert.equal(input.props.accept, 'video/mp4,.mp4'); assert.equal(input.props.tabIndex, -1);
  assert.equal(nodes(tree, node => node.type === 'label' && node.props.htmlFor === 'incident-video').length, 1);
  let opened = 0; input.props.ref.current = { value: '', click() { opened++; } };
  videoButton.props.onClick(); assert.equal(opened, 1, 'native button activation opens picker');
  nodes(tree, node => node.type === 'div' && typeof node.props.onDragOver === 'function')[0].props.onDragOver({ preventDefault() {} });
  let active = h.render();
  let activeButton = nodes(active, node => node.type === 'button' && node.props['aria-label'] === 'Choose Video file')[0];
  assert.match(activeButton.props.className, /upload-dropzone/);
  const validVideo = { name: 'dashcam.mp4', type: 'video/mp4', size: 100, lastModified: 1 };
  activeButton.props.onDrop({ preventDefault() {}, dataTransfer: { files: [validVideo] } });
  active = h.render(); assert.ok(JSON.stringify(active).includes('dashcam.mp4'));
  const activeInput = nodes(active, node => node.type === 'input' && node.props.id === 'incident-video')[0];
  activeInput.props.ref.current = { value: 'bad.txt' };
  activeInput.props.onChange({ target: { files: [{ name: 'bad.txt', type: 'text/plain', size: 40 }] } });
  const invalid = h.render();
  assert.ok(JSON.stringify(invalid).includes('dashcam.mp4'), 'invalid replacement leaves selected valid video intact');
  assert.ok(nodes(invalid, node => node.type === 'p' && node.props.role === 'alert').some(node => String(node.props.children).includes('MP4')));
  assert.equal(activeInput.props.ref.current.value, '', 'invalid selection resets input so the same file can be selected again');
});

test('telemetry drop accepts CSV and rejects non-CSV with a screen-reader alert', () => {
  const mocks = {
    react: {}, 'react/jsx-runtime': { jsx: (type, props) => ({ type, props: props || {} }), jsxs: (type, props) => ({ type, props: props || {} }), Fragment: 'fragment' },
    'next/link': { default: 'a' }, 'next/navigation': { useRouter: () => ({ push() {} }) }, '@/components/icons': new Proxy({}, { get: (_target, key) => String(key) }),
    '@/components/ui/button': { Button: 'button' }, '@/lib/format': { formatFileSize: size => `${size} bytes` }, '@/services/incident.service': { uploadIncident: async () => ({ incident_id: 'R1' }) },
  };
  // A separate harness instance keeps hook state isolated from the video case.
  const h = harness('components/incidents/upload-form.tsx', mocks);
  let tree = h.render();
  let button = nodes(tree, node => node.type === 'button' && node.props['aria-label'] === 'Choose Telemetry log file')[0];
  button.props.onDrop({ preventDefault() {}, dataTransfer: { files: [{ name: 'wrong.json', type: 'application/json', size: 10 }] } });
  tree = h.render(); assert.ok(nodes(tree, node => node.type === 'p' && node.props.role === 'alert').some(node => String(node.props.children).includes('CSV')));
  button = nodes(tree, node => node.type === 'button' && node.props['aria-label'] === 'Choose Telemetry log file')[0];
  const accepted = { name: 'telemetry.csv', type: 'text/csv', size: 50 };
  button.props.onDrop({ preventDefault() {}, dataTransfer: { files: [accepted] } });
  tree = h.render(); assert.ok(JSON.stringify(tree).includes('telemetry.csv'));
  const input = nodes(tree, node => node.type === 'input' && node.props.id === 'incident-telemetry')[0];
  input.props.ref.current = { value: 'wrong.json' };
  input.props.onChange({ target: { files: [{ name: 'wrong.json', type: 'application/json', size: 10 }] } });
  tree = h.render(); assert.ok(JSON.stringify(tree).includes('telemetry.csv'));
  assert.ok(nodes(tree, node => node.type === 'p' && node.props.role === 'alert').some(node => String(node.props.children).includes('CSV')));
  assert.equal(nodes(tree, node => node.type === 'input' && node.props.id === 'incident-telemetry')[0].props['aria-invalid'], true);
});

test('incident filters expose their selected state and announce updated results', () => {
  const source = fs.readFileSync(path.join(frontend, 'components/incidents/incident-list.tsx'), 'utf8');
  assert.match(source, /role="group" aria-label="Filter reports by review status across accessible incidents"/);
  assert.match(source, /aria-pressed=\{reviewFilter === value\}/);
  assert.match(source, /select aria-label="Processing status"/);
  assert.match(source, /role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(source, /\{listing\.total\} matching incidents\. Showing \{filteredIncidents\.length\} on this page\./);
});

function uploadFixture() {
  const requests = [], routes = [];
  const h = harness('components/incidents/upload-form.tsx', {
    'react/jsx-runtime': { jsx: (type, props) => ({ type, props: props || {} }), jsxs: (type, props) => ({ type, props: props || {} }) },
    'next/link': { default: 'a' }, 'next/navigation': { useRouter: () => ({ push: url => routes.push(url) }) },
    '@/components/icons': new Proxy({}, { get: (_target, key) => String(key) }), '@/components/ui/button': { Button: 'button' }, '@/lib/format': { formatFileSize: size => size + ' bytes' },
    '@/services/incident.service': { uploadIncident: (input, options) => new Promise((resolve, reject) => requests.push({ input, options, resolve, reject })) },
  });
  let tree = h.render(); nodes(tree, n => n.type === 'input' && n.props.id === 'incident-video')[0].props.onChange({ target: { files: [{ name: 'first.mp4', type: 'video/mp4', size: 100 }] } });
  tree = h.render(); nodes(tree, n => n.type === 'input' && n.props.id === 'incident-telemetry')[0].props.onChange({ target: { files: [{ name: 'log.csv', size: 20 }] } });
  return { ...h, requests, routes };
}
function content(node) { if (node == null || typeof node === 'boolean') return ''; if (Array.isArray(node)) return node.map(content).join(''); return typeof node === 'object' ? content(node.props?.children) : String(node); }
const button = (tree, name) => nodes(tree, n => n.type === 'button' && content(n).trim() === name)[0];
async function flush() { for (let i = 0; i < 10; i++) await Promise.resolve(); }
test('pending upload locks files/drop/remove, sends the displayed files once and shows byte progress then waiting phase', async () => {
  const f = uploadFixture(), submit = nodes(f.render(), n => n.type === 'button' && content(n).startsWith('Create Incident'))[0];
  submit.props.onClick(); submit.props.onClick(); assert.equal(f.requests.length, 1);
  let tree = f.render(); assert.ok(nodes(tree, n => n.type === 'input' && n.props.type === 'file').every(n => n.props.disabled));
  assert.ok(nodes(tree, n => n.type === 'button' && content(n).includes('Remove file')).every(n => n.props.disabled));
  const choose = nodes(tree, n => n.props['aria-label'] === 'Choose Video file')[0];
  choose.props.onDrop({ preventDefault() {}, dataTransfer: { files: [{ name: 'changed.mp4', type: 'video/mp4', size: 50 }] } });
  button(tree, 'Remove file').props.onClick(); tree = f.render(); assert.ok(content(tree).includes('first.mp4')); assert.equal(f.requests[0].input.video.name, 'first.mp4');
  f.requests[0].options.onProgress(50, 100); tree = f.render(); assert.equal(nodes(tree, n => n.type === 'progress')[0].props.value, 50);
  f.requests[0].options.onUploaded(); tree = f.render(); assert.ok(content(tree).includes('Waiting for server response')); f.unmount();
});
test('cancel aborts, keeps both files, permits retry and ignores stale progress and success', async () => {
  const f = uploadFixture(); nodes(f.render(), n => n.type === 'button' && content(n).startsWith('Create Incident'))[0].props.onClick();
  button(f.render(), 'Cancel upload').props.onClick(); assert.equal(f.requests[0].options.signal.aborted, true);
  let tree = f.render(); assert.ok(content(tree).includes('first.mp4')); assert.ok(content(tree).includes('log.csv'));
  nodes(tree, n => n.type === 'button' && content(n).startsWith('Create Incident'))[0].props.onClick(); assert.equal(f.requests.length, 2);
  f.requests[0].options.onProgress(90, 100); f.requests[0].resolve({ incident_id: 'OLD' }); await flush();
  tree = f.render(); assert.deepEqual(f.routes, []); assert.equal(nodes(tree, n => n.type === 'progress')[0].props.value, undefined);
  f.requests[1].resolve({ incident_id: 'NEW' }); await flush(); assert.deepEqual(f.routes, ['/incidents/NEW/processing']);
  tree = f.render(); assert.ok(nodes(tree, n => n.type === 'button' && content(n).includes('Uploading')).every(n => n.props.disabled)); f.unmount();
});
test('network error preserves both files for retry; unmount aborts retry and suppresses late navigation', async () => {
  const f = uploadFixture(); nodes(f.render(), n => n.type === 'button' && content(n).startsWith('Create Incident'))[0].props.onClick();
  f.requests[0].reject(new Error('offline')); await flush(); let tree = f.render();
  assert.ok(content(tree).includes('first.mp4')); assert.ok(content(tree).includes('log.csv')); assert.ok(content(tree).includes('offline'));
  nodes(tree, n => n.type === 'button' && content(n).startsWith('Create Incident'))[0].props.onClick();
  f.unmount(); assert.equal(f.requests[1].options.signal.aborted, true); f.requests[1].resolve({ incident_id: 'OLD' }); await flush(); assert.deepEqual(f.routes, []);
});
