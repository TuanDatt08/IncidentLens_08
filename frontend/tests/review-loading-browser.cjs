// Production Edge with intercepted API fixtures; not live backend E2E.
const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs'), path = require('node:path');
const base = process.env.REVIEW_LOADING_BASE_URL || 'http://127.0.0.1:3102';
const out = path.join(__dirname, '../test-results/review-loading'), results = [];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const gate = () => { let resolve; const promise = new Promise(r => resolve = r); return { promise, resolve }; };
const metadata = id => ({ incident_id: id, processing_status: 'COMPLETED', created_at: '2026-10-12T00:00:00Z', updated_at: '2026-10-12T00:00:00Z', incident_record: { scenario: 'metadata-' + id }, video_metadata: { duration: 10, width: 320, height: 240, collision_offset_in_video_s: 0 } });
const report = id => ({ incident_id: id, incident_detected: true, incident_type: 'COLLISION', incident_window: { start: 0, critical: 1, end: 2 }, summary: 'report-' + id, timeline: [], observations: [], key_factors: [], unknowns: [], evidence_ids: [], review_status: 'DRAFT', version: 1, created_at: null, updated_at: null });
const evidence = id => ({ items: [{ evidence_id: 'evidence-' + id, kind: 'frame', time_range_s: [1, 1], sha256: 'a'.repeat(64), bytes: 10, media_type: 'image/jpeg', tier: 'primary' }] });
const body = (id, part) => part === 'metadata' ? metadata(id) : part === 'report' ? report(id) : part === 'evidence' ? evidence(id) : { incident_id: id, items: [{ action: 'audit-' + id, actor: 'fixture', created_at: '2026-10-12T00:00:00Z', metadata: {} }] };
async function visible(page, part, id = 'I1') {
  if (part === 'metadata') await page.getByText('metadata-' + id, { exact: true }).waitFor();
  else if (part === 'report') await page.getByRole('heading', { name: 'Incident Summary' }).waitFor();
  else await page.getByText('evidence-' + id, { exact: true }).waitFor();
}
async function scenario(browser, width, name, test) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await context.newPage(), counts = {}, requests = [];
  await page.route('https://fonts.googleapis.com/**', route => route.abort());
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/auth/me')) return route.fulfill({ json: { csrf_token: 'fixture', user: { id: 'fixture', email: 'fixture@example.com', display_name: 'Review fixture', roles: ['engineer'], is_active: true, must_change_password: false } } });
    if (url.pathname.endsWith('/video')) return route.abort();
    if (url.pathname.endsWith('/incidents')) return route.fulfill({ json: { items: ['I1', 'I2'].map(metadata), total: 2, limit: 20, offset: 0 } });
    const match = url.pathname.match(/\/incidents\/(I\d)(?:\/(report|evidence|audit))?$/);
    if (!match) return route.fulfill({ json: {} });
    const id = match[1], part = match[2] || 'metadata', key = id + ':' + part;
    counts[key] = (counts[key] || 0) + 1;
    requests.push({ id, part, method: route.request().method(), at: Date.now() });
    await test.route(route, id, part, counts);
  });
  try { await test(page, counts); results.push({ width, name, pass: true, counts, requests }); }
  catch (error) { results.push({ width, name, pass: false, error: error.message, counts, requests }); }
  await page.screenshot({ path: path.join(out, `${width}-${name}.png`), fullPage: true });
  await context.close(); console.log(JSON.stringify({ ...results.at(-1), requests: undefined }));
}
async function main() {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    for (const width of [1440, 375]) {
      for (const fast of ['metadata', 'report', 'evidence']) {
        const hold = gate();
        const test = async (page, counts) => {
          await page.goto(base + '/incidents/I1', { waitUntil: 'domcontentloaded' });
          await visible(page, fast);
          for (const part of ['metadata', 'report', 'evidence'].filter(p => p !== fast)) await expect(page.getByRole('status').filter({ hasText: 'Loading ' + part })).toBeVisible();
          hold.resolve();
          for (const part of ['metadata', 'report', 'evidence']) await visible(page, part);
          await sleep(300); expect(counts['I1:audit']).toBe(1);
        };
        test.route = async (route, id, part) => { if (part !== fast && part !== 'audit') await hold.promise; await route.fulfill({ json: body(id, part) }).catch(() => {}); };
        await scenario(browser, width, fast + '-finishes-first', test); hold.resolve();
      }
      for (const failed of ['metadata', 'report', 'evidence', 'audit']) {
        const test = async (page, counts) => {
          await page.goto(base + '/incidents/I1');
          const retry = page.getByRole('button', { name: 'Retry ' + failed, exact: true });
          await retry.waitFor();
          for (const part of ['metadata', 'report', 'evidence'].filter(p => p !== failed)) await visible(page, part);
          const before = { ...counts }; await retry.focus(); await page.keyboard.press('Enter');
          if (failed === 'audit') await page.getByText('audit-I1', { exact: true }).waitFor(); else await visible(page, failed);
          await expect(page.getByRole('alert').filter({ hasText: 'fixture-' + failed })).toHaveCount(0);
          for (const part of ['metadata', 'report', 'evidence', 'audit']) expect(counts['I1:' + part]).toBe(before['I1:' + part] + (part === failed ? 1 : 0));
          if (failed === 'evidence') { await expect(page.getByRole('button', { name: /View at/ })).toBeEnabled(); }
        };
        test.route = async (route, id, part, counts) => {
          await sleep(250);
          if (part === failed && counts[id + ':' + part] === 1) return route.fulfill({ status: 503, json: { error: { code: 'TEMP', message: 'fixture-' + part } } });
          return route.fulfill({ json: body(id, part) });
        };
        await scenario(browser, width, failed + '-error-isolated-retry', test);
      }
      const mutation = async (page, counts) => {
        await page.goto(base + '/incidents/I1'); await page.getByLabel('Summary text').waitFor();
        await expect.poll(() => counts['I1:audit']).toBe(1);
        await page.getByLabel('Summary text').fill('edited summary');
        await page.getByRole('button', { name: 'Save Changes' }).click();
        await expect.poll(() => counts['I1:audit']).toBe(2);
        await sleep(300); expect(counts['I1:audit']).toBe(2);
      };
      mutation.route = (route, id, part) => route.fulfill({ json: part === 'report' && route.request().method() === 'PATCH' ? { ...report(id), ...route.request().postDataJSON(), version: 2 } : body(id, part) });
      await scenario(browser, width, 'single-initial-audit-refresh-after-save', mutation);
      const old = gate(), next = gate();
      const navigation = async (page, counts) => {
        await page.goto(base + '/incidents/I1');
        await page.getByRole('heading', { name: 'I1', exact: true }).waitFor();
        await expect.poll(() => counts['I1:metadata']).toBe(1);
        await page.getByRole('link', { name: 'Back to incidents', exact: true }).click();
        await page.getByRole('link').filter({ hasText: 'I2' }).filter({ visible: true }).first().click();
        await page.getByRole('heading', { name: 'I2', exact: true }).waitFor();
        old.resolve(); await sleep(500);
        await expect(page.getByText('metadata-I1', { exact: true })).toHaveCount(0);
        await expect(page.getByRole('heading', { name: 'Incident Summary' })).toHaveCount(0);
        await expect(page.getByText('evidence-I1', { exact: true })).toHaveCount(0);
        await expect(page.getByText('audit-I1', { exact: true })).toHaveCount(0);
        next.resolve(); for (const part of ['metadata', 'report', 'evidence']) await visible(page, part, 'I2');
        await expect(page.getByLabel('Summary text')).toHaveValue('report-I2');
      };
      navigation.route = async (route, id, part) => { await (id === 'I1' ? old.promise : next.promise); await route.fulfill({ json: body(id, part) }).catch(() => {}); };
      await scenario(browser, width, 'rapid-navigation-old-response-ignored', navigation); old.resolve(); next.resolve();
    }
  } finally { await browser.close(); fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ at: new Date().toISOString(), mode: 'Production Edge, controlled API fixtures and delayed responses; video aborted', results }, null, 2)); }
  if (results.some(result => !result.pass)) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
