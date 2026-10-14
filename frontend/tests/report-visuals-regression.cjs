const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const loaded = { exports: {} };
let requests = 0, moves = 0, lines = 0, revoked = 0;
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=';
const context = { fillRect() {}, fillText() {}, strokeRect() {}, beginPath() {}, stroke() {}, drawImage() {}, moveTo() { moves++; }, lineTo() { lines++; } };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/report-visuals.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, {
  exports: loaded.exports, module: loaded, DOMException,
  require() { return { apiFetch: async () => { requests++; return { ok: true, headers: { get: () => '1000' }, blob: async () => ({ size: 1000, type: 'image/jpeg' }) }; } }; },
  URL: { createObjectURL: () => 'blob:fixture', revokeObjectURL: () => { revoked++; } },
  Image: class { naturalWidth = 800; naturalHeight = 450; async decode() {} },
  document: { createElement: () => ({ getContext: () => context, toDataURL: () => 'data:image/png;base64,' + png }) },
});
(async () => {
  const frame = { kind: 'frame', media_type: 'image/jpeg', evidence_id: 'EVD', time_range_s: [-1, -1], sha256: 'a'.repeat(64) };
  const result = await loaded.exports.prepareReportFigures('INC', Array(5).fill(frame), { state: 'available', alignment: 'UNKNOWN', time_basis: 'log_seconds' }, { aborted: false });
  assert.equal(requests, 4); assert.equal(revoked, 4); assert.equal(result.figures.length, 4);
  assert.ok(result.notes.some(note => note.includes('omitted')));
  const chart = await loaded.exports.prepareReportFigures('INC', [], { state: 'available', alignment: 'VERIFIED', time_basis: 'video_seconds', downsampled: true, signals: [{ label: 'Speed', unit: 'km/h', samples: [{ time_s: 0, value: 40 }, { time_s: 1, value: null }, { time_s: 2, value: 20 }] }] }, { aborted: false });
  assert.equal(chart.figures.length, 1); assert.match(chart.figures[0].caption, /downsampled/);
  assert.equal(moves, 2); assert.equal(lines, 0, 'null values must break the plot rather than become zero or connected data');
  await assert.rejects(loaded.exports.prepareReportFigures('INC', [frame], undefined, { aborted: true }), /cancelled/);
  console.log('PASS: bounded authenticated frame reads, revoked blob URLs, unknown alignment omission, chart gaps and cancelled export');
})().catch(error => { console.error(error); process.exitCode = 1; });
