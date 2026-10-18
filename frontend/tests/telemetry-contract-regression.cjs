const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

function service(context) {
  const exports = {};
  const calls = [];
  vm.runInNewContext(ts.transpileModule(fs.readFileSync('services/telemetry.service.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText, { exports, require(name) {
    if (name === '@/lib/config') return { AUTH_ENABLED: true, USE_MOCK_API: false };
    return { apiRequest: async (...args) => { calls.push(args); return context; } };
  } });
  return { read: exports.getIncidentTelemetry, calls };
}

test('incident charts consume review-context JSON, preserving backend units, timestamps and gaps', async () => {
  const { read, calls } = service({ time_basis: 'video_seconds', alignment: 'VERIFIED', telemetry_error: null,
    points: [{ time_s: 4, speed_kmh: 36, brake_pct: null, acceleration: -2 }] });
  const signal = new AbortController().signal;
  const chart = await read('INC /1', signal);
  assert.equal(calls[0][0], '/incidents/INC%20%2F1/review-context');
  assert.equal(calls[0][1].signal, signal);
  assert.equal(chart.state, 'available');
  assert.equal(chart.signals[0].unit, 'km/h');
  assert.equal(chart.signals[0].samples[0].time_s, 4);
  assert.equal(chart.signals[0].samples[0].value, 36);
  assert.equal(chart.signals[1].samples[0].value, null);
  assert.equal(chart.signals[2].samples[0].value, -2);
});

test('unverified alignment preserves backend limitation and exposes no chart samples', async () => {
  const { read } = service({ time_basis: 'video_seconds', alignment: 'UNKNOWN', points: [], telemetry_error: 'Unverified alignment.' });
  const chart = await read('INC1');
  assert.equal(chart.state, 'unavailable');
  assert.equal(chart.message, 'Unverified alignment.');
  assert.equal(chart.signals.length, 0);
});
