const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const loaded = { exports: {} };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/report-export.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, { module: loaded, exports: loaded.exports, TextEncoder, Uint8Array, DataView, Date, atob });
const { normalizeReport, reportDocx, printableReport, exportFilename } = loaded.exports;
const saved = { version: 3, analysis: { review_status: 'DRAFT', time_basis: 'video_seconds', summary: '<script>alert("x")</script> & tiếng Việt', timeline: [{ time_s: 4.2, observation: 'Vehicle stopped', evidence_ids: ['ev-1'] }], factors: [{ label: 'Wet road', claim_status: 'OBSERVED' }], unknowns: [null] } };
saved.analysis.summary += '\r\nSecond line\nThird line';
const doc = normalizeReport('id/../../', saved, '2026-10-12T00:00:00Z');
assert.equal(doc.version, '3'); assert.equal(doc.status, 'DRAFT');
assert.ok(doc.sections.find(s => s.title === 'Timeline').lines[0].includes('Vehicle stopped'));
assert.ok(doc.sections.find(s => s.title === 'Incident').lines.some(s => s.includes('video_seconds')));
assert.equal(normalizeReport('empty', null).sections[0].lines[0], 'Unknown');
const html = printableReport(doc); assert.ok(!html.includes('<script>')); assert.ok(html.includes('&lt;script&gt;')); assert.ok(html.includes('UNAPPROVED REPORT')); assert.ok(!html.includes('<iframe')); assert.ok(!html.includes('<img'));
assert.ok(!printableReport(normalizeReport('approved', { review_status: 'APPROVED' })).includes('UNAPPROVED REPORT'));
assert.ok(!exportFilename('../../bad id', 'json').includes('/'));
const zip = Buffer.from(reportDocx(doc)); const entries = new Map(); let offset = 0;
function crc32(data) { let crc = 0xffffffff; for (const byte of data) { crc ^= byte; for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); } return (crc ^ 0xffffffff) >>> 0; }
while (zip.readUInt32LE(offset) === 0x04034b50) {
  const size = zip.readUInt32LE(offset + 18); const nameLength = zip.readUInt16LE(offset + 26); const extraLength = zip.readUInt16LE(offset + 28);
  const name = zip.subarray(offset + 30, offset + 30 + nameLength).toString(); const start = offset + 30 + nameLength + extraLength; const data = zip.subarray(start, start + size);
  assert.equal(zip.readUInt32LE(offset + 14), crc32(data)); entries.set(name, data.toString()); offset = start + size;
}
for (const name of ['[Content_Types].xml', '_rels/.rels', 'word/document.xml', 'word/styles.xml', 'word/_rels/document.xml.rels']) assert.ok(entries.has(name));
assert.ok(entries.get('word/document.xml').includes('tiếng Việt')); assert.ok(entries.get('word/document.xml').includes('&lt;script&gt;'));
assert.ok(entries.get('word/document.xml').includes('<w:br/><w:t xml:space="preserve">Second line</w:t><w:br/><w:t xml:space="preserve">Third line</w:t>'));
assert.equal(zip.readUInt32LE(offset), 0x02014b50); assert.equal(zip.readUInt32LE(zip.length - 22), 0x06054b50); assert.equal(zip.readUInt16LE(zip.length - 14), entries.size);
console.log('PASS: saved v1/v2 normalization, null values, safe markup, unapproved marking, sanitized filenames, valid OOXML ZIP parts/CRC/Unicode/central directory');
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=';
const visualDoc = { ...doc, figures: [{ caption: 'Frame <script>invalid</script>', pngBase64: png, width: 1, height: 1 }] };
assert.ok(printableReport(visualDoc).includes('data:image/png;base64,'));
assert.ok(!printableReport(visualDoc).includes('<script>'));
const visualZip = Buffer.from(reportDocx(visualDoc)); const parts = new Map(); offset = 0;
while (visualZip.readUInt32LE(offset) === 0x04034b50) {
  const size = visualZip.readUInt32LE(offset + 18), nameLength = visualZip.readUInt16LE(offset + 26);
  const name = visualZip.subarray(offset + 30, offset + 30 + nameLength).toString();
  const start = offset + 30 + nameLength, bytes = visualZip.subarray(start, start + size);
  assert.equal(visualZip.readUInt32LE(offset + 14), crc32(bytes)); parts.set(name, bytes); offset = start + size;
}
assert.deepEqual(parts.get('word/media/image0.png'), Buffer.from(png, 'base64'));
assert.ok(parts.get('word/_rels/document.xml.rels').toString().includes('rIdImage0'));
assert.ok(parts.get('word/document.xml').toString().includes('r:embed="rIdImage0"'));
assert.ok(parts.get('[Content_Types].xml').toString().includes('image/png'));
assert.ok(!printableReport({ ...doc, figures: [{ caption: 'bad', pngBase64: 'javascript:alert(1)', width: 1, height: 1 }] }).includes('<img'));
console.log('PASS: embedded PNG bytes, drawing relationships, image content type and unsafe figure rejection');
