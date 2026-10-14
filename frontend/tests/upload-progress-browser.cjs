// Uses real HTTP upload bytes to a local fixture through Next's proxy, not the backend/AI.
const { chromium, expect } = require('@playwright/test');
const http = require('node:http'), fs = require('node:fs'), path = require('node:path');
const base = process.env.UPLOAD_BROWSER_BASE_URL || 'http://127.0.0.1:3102';
const out = path.join(__dirname, '../test-results/upload-progress'), results = [], received = [];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let mode = 'hold';
const server = http.createServer((req, res) => {
  if (req.url !== '/api/v1/incidents/upload') { res.writeHead(404); res.end(); return; }
  const entry = { index: received.length, mode, bytes: 0, csrf: req.headers['x-csrf-token'], cookie: req.headers.cookie, complete: false, closedBeforeResponse: false };
  received.push(entry); const chunks = [];
  req.on('data', chunk => { entry.bytes += chunk.length; chunks.push(chunk); });
  req.on('aborted', () => entry.aborted = true);
  res.on('close', () => { if (!res.writableEnded) entry.closedBeforeResponse = true; });
  req.on('end', () => {
    entry.complete = true; const body = Buffer.concat(chunks).toString('latin1');
    entry.hasVideo = body.includes('source.mp4'); entry.hasTelemetry = body.includes('log.csv');
    entry.release = () => { res.writeHead(entry.mode === 'error' ? 503 : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(entry.mode === 'error' ? { error: { code: 'TEMP', message: 'fixture upload failed' } } : { incident_id: 'NEW', processing_status: 'READY' })); };
  });
});
async function setup(browser, width) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  await context.addCookies([{ name: 'fixture_session', value: 'session', url: base }]);
  const page = await context.newPage();
  await page.addInitScript(() => {
    window.__uploadEvents = [];
    const send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(body) {
      this.upload.addEventListener('progress', e => window.__uploadEvents.push({ type: 'progress', loaded: e.loaded, total: e.total, at: performance.now() }));
      this.upload.addEventListener('load', () => window.__uploadEvents.push({ type: 'sent', at: performance.now() }));
      this.addEventListener('abort', () => window.__uploadEvents.push({ type: 'abort', at: performance.now() }));
      return send.call(this, body);
    };
  });
  await page.route('https://fonts.googleapis.com/**', route => route.abort());
  await page.route('**/api/v1/auth/me', route => route.fulfill({ json: { csrf_token: 'fixture-csrf', user: { id: 'fixture', email: 'fixture@example.com', display_name: 'Upload fixture', roles: ['engineer'], is_active: true, must_change_password: false } } }));
  await page.route('**/api/v1/incidents/NEW', route => route.fulfill({ json: { incident_id: 'NEW', processing_status: 'READY', video_metadata: null } }));
  await page.route('**/api/v1/incidents?**', route => route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } }));
  await page.goto(base + '/incidents/new');
  await page.locator('#incident-video').setInputFiles({ name: 'source.mp4', mimeType: 'video/mp4', buffer: Buffer.alloc(2 * 1024 * 1024, 1) });
  await page.locator('#incident-telemetry').setInputFiles({ name: 'log.csv', mimeType: 'text/csv', buffer: Buffer.from('time,value\n0,1\n') });
  const cdp = await context.newCDPSession(page); await cdp.send('Network.enable');
  return { context, page, cdp };
}
async function scenario(browser, width, name, test) {
  const { context, page, cdp } = await setup(browser, width); const start = received.length;
  try { await test(page, cdp); results.push({ width, name, pass: true, received: received.slice(start).map(({ release, ...entry }) => entry) }); }
  catch (error) { results.push({ width, name, pass: false, error: error.message, received: received.slice(start).map(({ release, ...entry }) => entry) }); }
  await page.screenshot({ path: path.join(out, `${width}-${name}.png`), fullPage: true });
  results.at(-1).lastPageEvents = await page.evaluate(() => window.__uploadEvents);
  await context.close(); console.log(JSON.stringify({ ...results.at(-1), lastPageEvents: undefined }));
}
async function throttle(cdp, bytes = 256 * 1024) { await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 20, downloadThroughput: 4 * 1024 * 1024, uploadThroughput: bytes }); }
async function main() {
  fs.mkdirSync(out, { recursive: true }); await new Promise(resolve => server.listen(3112, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    for (const width of [1440, 375]) {
      await scenario(browser, width, 'slow-progress-cancel-error-retry', async (page, cdp) => {
        mode = 'hold'; await throttle(cdp);
        await page.getByRole('button', { name: /Create Incident/ }).click();
        await expect.poll(() => page.evaluate(() => window.__uploadEvents.some(e => e.type === 'progress' && e.loaded > 0 && e.loaded < e.total)), { timeout: 15000 }).toBe(true);
        await expect(page.getByRole('progressbar', { name: 'File upload progress' })).toHaveAttribute('value', /[1-9]/);
        await expect(page.getByRole('button', { name: 'Choose Video file' })).toBeDisabled();
        await expect(page.getByRole('button', { name: 'Choose Telemetry log file' })).toBeDisabled();
        for (const remove of await page.getByRole('button', { name: 'Remove file' }).all()) await expect(remove).toBeDisabled();
        await page.getByRole('button', { name: 'Choose Video file' }).evaluate(el => { const dt = new DataTransfer(); dt.items.add(new File(['x'], 'other.mp4', { type: 'video/mp4' })); el.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: dt })); });
        await expect(page.getByRole('button', { name: 'Choose Video file' })).toContainText('source.mp4');
        await page.getByRole('button', { name: 'Cancel upload' }).focus(); await page.keyboard.press('Enter');
        await expect.poll(() => page.evaluate(() => window.__uploadEvents.some(e => e.type === 'abort'))).toBe(true);
        await expect(page).toHaveURL(base + '/incidents/new');
        await expect(page.getByRole('button', { name: /Create Incident/ })).toBeEnabled();
        mode = 'error'; await throttle(cdp, 1024 * 1024);
        await page.getByRole('button', { name: /Create Incident/ }).click();
        await page.getByRole('status').filter({ hasText: 'Waiting for server response' }).waitFor({ timeout: 20000 });
        await expect.poll(() => received.some(e => e.mode === 'error' && e.complete)).toBe(true);
        received.findLast(e => e.mode === 'error' && e.complete).release();
        await page.getByRole('alert').filter({ hasText: 'fixture upload failed' }).waitFor();
        await expect(page.getByRole('button', { name: 'Choose Video file' })).toContainText('source.mp4');
        await expect(page.getByRole('button', { name: 'Choose Telemetry log file' })).toContainText('log.csv');
        mode = 'success'; await page.getByRole('button', { name: /Create Incident/ }).click();
        await page.getByRole('status').filter({ hasText: 'Waiting for server response' }).waitFor({ timeout: 20000 });
        await expect.poll(() => received.some(e => e.mode === 'success' && e.complete)).toBe(true);
        const latest = received.findLast(e => e.mode === 'success' && e.complete);
        expect(latest.csrf).toBe('fixture-csrf'); expect(latest.cookie).toContain('fixture_session=session'); expect(latest.hasVideo).toBe(true); expect(latest.hasTelemetry).toBe(true);
        latest.release(); await expect(page).toHaveURL(base + '/incidents/NEW/processing');
        await expect(page.getByRole('button', { name: 'Start analysis' })).toBeVisible();
      });
      await scenario(browser, width, 'cancel-waiting-late-response', async (page, cdp) => {
        mode = 'hold'; await throttle(cdp, 1024 * 1024);
        const before = received.length;
        await page.getByRole('button', { name: /Create Incident/ }).click();
        await page.getByRole('status').filter({ hasText: 'Waiting for server response' }).waitFor({ timeout: 20000 });
        await expect.poll(() => received.length).toBe(before + 1);
        const old = received.at(-1); await expect.poll(() => old.complete).toBe(true);
        await page.screenshot({ path: path.join(out, `${width}-waiting-server.png`), fullPage: true });
        await page.getByRole('button', { name: 'Cancel upload' }).click(); old.release(); await sleep(700);
        await expect(page).toHaveURL(base + '/incidents/new');
        await expect(page.getByRole('button', { name: /Create Incident/ })).toBeEnabled();
        await expect(page.getByRole('button', { name: 'Choose Video file' })).toContainText('source.mp4');
      });
    }
  } finally {
    await browser.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ at: new Date().toISOString(), mode: 'Edge production frontend; real HTTP local upload fixture; CDP upload throughput 256KiB/s and 1MiB/s', results }, null, 2));
  }
  if (results.some(result => !result.pass)) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
