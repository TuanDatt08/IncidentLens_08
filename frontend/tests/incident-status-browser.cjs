// Production browser fixture verification, not live backend E2E.
const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.INCIDENT_STATUS_BASE_URL || 'http://127.0.0.1:3102';
const output = path.join(__dirname, '../test-results/incident-status');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const results = [];
const incident = status => ({ incident_id: 'I1', processing_status: status, video_metadata: { duration: 10, width: 320, height: 240 }, incident_record: null });
const job = status => ({ job_id: 'J1', status, pass: 1, progress: { done: 1, total: 10 }, error: status === 'failed' ? { code: 'FAILED', message: 'fixture analysis failed' } : null });
async function scenario(browser, width, role, name, test) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await context.newPage(); const counts = { analyze: 0, jobs: 0, incidents: 0, report: 0, evidence: 0 }; const requests = [];
  await page.route('https://fonts.googleapis.com/**', route => route.abort());
  await page.route('**/api/**', async route => {
    const request = route.request(), url = new URL(request.url());
    requests.push({ method: request.method(), path: url.pathname });
    if (url.pathname.endsWith('/auth/me')) return route.fulfill({ json: { csrf_token: 'fixture', user: { id: 'fixture', email: 'fixture@example.com', display_name: 'Status fixture', roles: [role], is_active: true, must_change_password: false } } });
    if (url.pathname.endsWith('/analyze')) counts.analyze++;
    else if (url.pathname.includes('/jobs/')) counts.jobs++;
    else if (url.pathname.endsWith('/report')) counts.report++;
    else if (url.pathname.endsWith('/evidence')) counts.evidence++;
    else if (url.pathname.endsWith('/I1')) counts.incidents++;
    await test.route(route, url, counts);
  });
  try {
    await test(page, context, counts);
    results.push({ width, role, name, pass: true, counts, requests });
  } catch (error) { results.push({ width, role, name, pass: false, error: error.message, counts, requests }); }
  await page.screenshot({ path: path.join(output, `${width}-${role}-${name}.png`), fullPage: true });
  await context.close(); console.log(JSON.stringify({ ...results.at(-1), requests: undefined }));
}
async function main() {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    for (const width of [1440, 375]) {
      for (const status of ['READY', 'FAILED']) {
        let accepted = false;
        const test = async (page, context, counts) => {
          await page.goto(base + '/incidents/I1/processing');
          const action = page.getByRole('button', { name: status === 'READY' ? 'Start analysis' : 'Retry analysis', exact: true });
          await action.waitFor(); await sleep(300); expect(counts.analyze).toBe(0);
          await page.reload(); await action.waitFor(); expect(counts.analyze).toBe(0);
          await action.focus(); await page.keyboard.press('Enter');
          await expect.poll(() => counts.analyze).toBe(1);
          await expect(page.getByRole('button', { name: 'Starting…', exact: true })).toBeDisabled();
          await page.getByText('J1', { exact: false }).first().waitFor();
          await page.reload(); await page.getByRole('heading', { name: /Pass 1:/ }).waitFor();
          expect(counts.analyze).toBe(1); expect(counts.jobs).toBeGreaterThanOrEqual(2);
          await page.getByRole('link', { name: 'Back to incidents', exact: true }).click();
          const stopped = counts.jobs; await sleep(2300); expect(counts.jobs).toBe(stopped);
        };
        test.route = async (route, url) => {
          if (url.pathname.endsWith('/analyze')) { await sleep(900); accepted = true; return route.fulfill({ json: { job_id: 'J1', incident_id: 'I1', status: 'queued' } }); }
          if (url.pathname.includes('/jobs/')) return route.fulfill({ json: job('running') });
          if (url.pathname.endsWith('/incidents')) return route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } });
          return route.fulfill({ json: incident(accepted ? 'PROCESSING' : status) });
        };
        await scenario(browser, width, 'engineer', status.toLowerCase() + '-explicit-start-reload', test);
      }
      for (const role of ['reviewer', 'admin']) {
        const test = async (page, context, counts) => {
          await page.goto(base + '/incidents/I1/processing');
          await page.getByRole('heading', { name: 'Analysis failed. An Engineer can retry when ready.' }).waitFor();
          await expect(page.getByRole('button', { name: /Start analysis|Retry analysis/ })).toHaveCount(0);
          await page.reload(); await page.getByRole('heading', { name: 'Analysis failed. An Engineer can retry when ready.' }).waitFor();
          expect(counts.analyze).toBe(0);
        };
        test.route = route => route.fulfill({ json: incident('FAILED') });
        await scenario(browser, width, role, 'failed-view-only', test);
      }
      for (const terminalStatus of ['failed', 'cancelled']) {
        let started = false;
        const stoppedJob = async (page, context, counts) => {
          await context.addInitScript(() => { if (!sessionStorage.getItem('fixture-initialized')) { sessionStorage.setItem('analysis-job:I1', 'J1'); sessionStorage.setItem('fixture-initialized', 'yes'); } });
          await page.goto(base + '/incidents/I1/processing');
          await page.getByRole('button', { name: 'Retry analysis', exact: true }).waitFor();
          expect(counts.analyze).toBe(0);
          const stopped = counts.jobs; await sleep(2300); expect(counts.jobs).toBe(stopped);
          await page.reload(); await page.getByRole('button', { name: 'Retry analysis', exact: true }).waitFor();
          expect(counts.analyze).toBe(0);
          await page.getByRole('button', { name: 'Retry analysis', exact: true }).click();
          await expect.poll(() => counts.analyze).toBe(1);
          await page.getByRole('heading', { name: /Pass 1:/ }).waitFor();
        };
        stoppedJob.route = (route, url, counts) => {
          if (url.pathname.endsWith('/analyze')) { started = true; return route.fulfill({ json: { job_id: 'J1', status: 'queued', incident_id: 'I1' } }); }
          if (url.pathname.includes('/jobs/')) return route.fulfill({ json: job(started ? 'running' : terminalStatus) });
          return route.fulfill({ json: incident(started || counts.incidents === 1 ? 'PROCESSING' : 'FAILED') });
        };
        await scenario(browser, width, 'engineer', terminalStatus + '-stored-job-explicit-retry', stoppedJob);
      }
      const terminal = async (page, context, counts) => {
        await context.addInitScript(() => sessionStorage.setItem('analysis-job:I1', 'J1'));
        await page.goto(base + '/incidents/I1/processing');
        await page.getByRole('heading', { name: /Pass 1:/ }).waitFor();
        await page.getByRole('alert').filter({ hasText: 'temporary status error' }).waitFor();
        await page.getByRole('button', { name: 'Retry failed loads' }).waitFor();
        const stopped = counts.jobs;
        await page.getByRole('button', { name: 'Retry failed loads' }).click();
        await page.getByRole('button', { name: 'Open review' }).waitFor();
        await sleep(2300); expect(counts.jobs).toBe(stopped); expect(counts.analyze).toBe(0);
        expect(counts.report).toBe(2); expect(counts.evidence).toBe(1);
        expect(await page.evaluate(() => sessionStorage.getItem('analysis-job:I1'))).toBeNull();
      };
      terminal.route = (route, url, counts) => {
        if (url.pathname.includes('/jobs/')) {
          if (counts.jobs === 2) return route.fulfill({ status: 503, json: { error: { code: 'TEMP', message: 'temporary status error' } } });
          return route.fulfill({ json: job(counts.jobs < 3 ? 'running' : 'succeeded') });
        }
        if (url.pathname.endsWith('/report')) return counts.report === 1 ? route.fulfill({ status: 503, json: { error: { code: 'TEMP', message: 'report unavailable' } } }) : route.fulfill({ json: {} });
        if (url.pathname.endsWith('/evidence')) return route.fulfill({ json: { items: [] } });
        return route.fulfill({ json: incident('PROCESSING') });
      };
      await scenario(browser, width, 'reviewer', 'stored-job-recovery-completion', terminal);
      const unknown = async (page, context, counts) => {
        await page.goto(base + '/incidents/I1/processing');
        await page.getByRole('heading', { name: /Analysis is already running/ }).waitFor();
        await expect(page.getByRole('button', { name: /Start analysis|Retry analysis/ })).toHaveCount(0);
        await page.getByRole('button', { name: 'Open review' }).waitFor();
        const stopped = counts.incidents; await sleep(2300); expect(counts.incidents).toBe(stopped);
        expect(counts.analyze).toBe(0); expect(counts.jobs).toBe(0);
      };
      unknown.route = (route, url, counts) => url.pathname.endsWith('/evidence') ? route.fulfill({ json: { items: [] } }) : route.fulfill({ json: incident(counts.incidents < 2 ? 'PROCESSING' : 'COMPLETED') });
      await scenario(browser, width, 'engineer', 'unknown-job-read-only-completion', unknown);
    }
  } finally {
    await browser.close(); fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({ at: new Date().toISOString(), mode: 'Edge production browser; intercepted API fixtures, no live AI/backend', results }, null, 2));
  }
  if (results.some(result => !result.pass)) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
