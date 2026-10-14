/* Local-only browser fixture. Run: node frontend/tests/v2-polling-browser-fixture.cjs */
const http = require('node:http');
const HOST = '127.0.0.1';
const API_PORT = 8301;
const CONTROL_PORT = 8302;
let status = 'queued';
let delayMs = 0;
let offline = false;
let api;
let activeJobs = 0;
let maxActiveJobs = 0;
let jobRequests = 0;
let aborted = 0;
let events = [];
function json(response, data, code = 200) { response.writeHead(code, { 'Content-Type': 'application/json' }); response.end(JSON.stringify(data)); }
function job() { return { job_id: 'POLLING-TEST-JOB', recording_id: 'POLLING-BROWSER-TEST', status, stage: status === 'running' ? 'localization' : status, attempt: 1, progress: { done: status === 'succeeded' ? 10 : status === 'running' ? 3 : 0, total: 10 }, coverage: { unknowns: [] }, budget: { calls_used: 1, max_calls: 20 }, partial_results: [], error: status === 'failed' ? { code: 'FIXTURE_FAILED', message: 'Synthetic failure for polling verification.' } : null }; }
function serve(request, response) {
  response.setHeader('Access-Control-Allow-Origin', 'http://localhost:3101');
  response.setHeader('Access-Control-Allow-Credentials', 'true');
  response.setHeader('Access-Control-Allow-Headers', 'Content-Type,X-Requested-With,Idempotency-Key');
  response.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (request.method === 'OPTIONS') { response.writeHead(204); response.end(); return; }
  const url = new URL(request.url, 'http://127.0.0.1');
  const isJob = url.pathname.endsWith('/jobs');
  const entry = { path: url.pathname, start: Date.now(), end: null, status: null, aborted: false };
  events.push(entry);
  if (isJob) { jobRequests++; activeJobs++; maxActiveJobs = Math.max(maxActiveJobs, activeJobs); }
  let settled = false;
  const finish = () => { if (settled) return; settled = true; entry.end = Date.now(); if (isJob) activeJobs--; };
  response.on('finish', finish);
  response.on('close', () => { if (!settled) { entry.aborted = true; aborted++; finish(); } });
  const timer = setTimeout(() => {
    if (response.destroyed) return;
    if (url.pathname === '/api/v2/session') json(response, { subject: 'polling-fixture-engineer', roles: ['Engineer'] });
    else if (url.pathname === '/api/v2/recordings/POLLING-BROWSER-TEST/jobs') { entry.status = status; json(response, { items: [job()], next_cursor: null }); }
    else if (url.pathname === '/api/v2/recordings/POLLING-BROWSER-TEST/candidates') json(response, { items: [], next_cursor: null });
    else json(response, { error: { code: 'FIXTURE_NOT_FOUND', message: 'This local fixture only serves the polling test recording.' } }, 404);
  }, delayMs);
  response.on('close', () => clearTimeout(timer));
}
async function setOffline(value) {
  if (value === offline) return;
  offline = value;
  if (value) {
    const current = api;
    api = undefined;
    if (current) await new Promise(resolve => { current.close(resolve); current.closeAllConnections(); });
  } else await startApi();
}
async function startApi() { api = http.createServer(serve); await new Promise((resolve, reject) => { api.once('error', reject); api.listen(API_PORT, HOST, resolve); }); }
const control = http.createServer(async (request, response) => {
  if (request.url === '/metrics' && request.method === 'GET') { json(response, { status, offline, delayMs, activeJobs, maxActiveJobs, jobRequests, aborted, events }); return; }
  if (request.url !== '/control' || request.method !== 'POST') { json(response, { error: 'not found' }, 404); return; }
  try {
    let body = ''; for await (const chunk of request) body += chunk;
    const input = JSON.parse(body);
    if (input.status !== undefined) { if (!['queued','running','succeeded','failed','cancelled'].includes(input.status)) throw new Error('invalid status'); status = input.status; }
    if (input.delayMs !== undefined) { if (!Number.isInteger(input.delayMs) || input.delayMs < 0 || input.delayMs > 30000) throw new Error('invalid delay'); delayMs = input.delayMs; }
    if (input.resetMetrics) { if (activeJobs) throw new Error('wait until no jobs are in flight'); jobRequests = 0; maxActiveJobs = 0; aborted = 0; events = []; }
    if (input.offline !== undefined) await setOffline(!!input.offline);
    json(response, { status, delayMs, offline });
  } catch (error) { json(response, { error: error.message }, 400); }
});
(async () => { await startApi(); control.listen(CONTROL_PORT, HOST, () => process.stdout.write('Polling fixture ready: API 8301, control 8302\n')); })().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
function shutdown() { api?.closeAllConnections(); api?.close(); control.closeAllConnections(); control.close(() => process.exit(0)); }
process.on('SIGINT', shutdown); process.on('SIGTERM', shutdown);
