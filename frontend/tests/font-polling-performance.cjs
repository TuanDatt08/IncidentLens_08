// Production browser measurements with controlled fixtures, not live API timings.
const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.PERFORMANCE_BASE_URL || 'http://127.0.0.1:3102';
const phase = process.argv[2] || 'baseline';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const identity = { csrf_token: 'fixture', user: { id: 'fixture', email: 'fixture@example.com', display_name: 'Performance fixture', roles: ['engineer'], is_active: true, must_change_password: false } };
async function setup(browser, fontDelay) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage(); const fonts = [];
  await page.addInitScript(() => {
    window.__metrics = { lcp: 0, cls: 0, jobs: [] };
    new PerformanceObserver(list => { for (const entry of list.getEntries()) window.__metrics.lcp = entry.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
    new PerformanceObserver(list => { for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.__metrics.cls += entry.value; }).observe({ type: 'layout-shift', buffered: true });
    new MutationObserver(() => {
      const text = [...document.querySelectorAll('h2')].find(el => el.textContent.startsWith('Analysis: '))?.textContent;
      if (text && window.__metrics.jobs.at(-1)?.text !== text) window.__metrics.jobs.push({ text, at: performance.now() });
    }).observe(document, { childList: true, subtree: true, characterData: true });
  });
  page.on('requestfinished', req => { if (/fonts\.(googleapis|gstatic)\.com/.test(req.url())) fonts.push({ url: req.url(), status: 'finished' }); });
  page.on('requestfailed', req => { if (/fonts\.(googleapis|gstatic)\.com/.test(req.url())) fonts.push({ url: req.url(), status: 'failed', error: req.failure()?.errorText }); });
  if (fontDelay !== null) await page.route('https://fonts.googleapis.com/**', async route => {
    await sleep(fontDelay);
    // Empty stylesheet isolates the blocking CSS dependency; it does NOT measure font bytes/CLS.
    await route.fulfill({ contentType: 'text/css', body: '/* controlled stylesheet response */' });
  });
  return { context, page, fonts };
}
async function verifyRecovery(browser) {
  const { context, page } = await setup(browser, null);
  let jobs = 0;
  await page.route('https://fonts.googleapis.com/**', route => route.abort('failed'));
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url()); let body;
    if (url.pathname.endsWith('/auth/me')) body = identity;
    else if (url.pathname.endsWith('/jobs')) {
      const index = jobs++;
      if (index === 1) return route.fulfill({ status: 503, json: { error: { code: 'TEMPORARY_FAILURE', message: 'fixture temporarily offline' } } });
      const status = index === 0 ? 'queued' : index === 2 ? 'running' : 'succeeded';
      body = { items: [{ job_id: 'J1', status, stage: 'PASS_1', progress: { done: index, total: 3 }, budget: { calls_used: 0, max_calls: 10 }, partial_results: [], coverage: {}, error: null }], next_cursor: null };
    } else if (url.pathname.endsWith('/session')) body = { subject: 'fixture', roles: ['Engineer'] };
    else body = { items: [], next_cursor: null };
    await route.fulfill({ json: body });
  });
  try {
    await page.goto(base + '/recordings/R1', { waitUntil: 'commit' });
    await page.getByRole('heading', { name: 'Analysis: queued', exact: true }).waitFor();
    await page.getByRole('alert').filter({ hasText: 'fixture temporarily offline' }).waitFor();
    await page.getByRole('heading', { name: 'Analysis: running', exact: true }).waitFor();
    await page.getByRole('heading', { name: 'Analysis: succeeded', exact: true }).waitFor();
    await sleep(2500);
    assert.equal(jobs, 4, 'polling must recover once and stop after terminal status');
    assert.equal(await page.getByRole('alert').filter({ hasText: 'fixture temporarily offline' }).count(), 0);
    assert.deepEqual(await page.evaluate(() => window.__metrics.jobs.map(item => item.text)), ['Analysis: queued', 'Analysis: running', 'Analysis: succeeded']);
    assert.equal(await page.evaluate(() => [...document.fonts].some(font => font.family === 'Mulish' && font.status === 'loaded')), false);
    await page.getByRole('button', { name: 'Account menu' }).click(); await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('button', { name: 'Account menu' }).evaluate(el => el.parentElement.open), false);
    console.log('PASS: font failure keeps fallback/interaction; polling recovers from 503, clears error and stops after succeeded');
  } catch (error) {
    console.error('Recovery diagnostic', JSON.stringify({ jobs, url: page.url(), state: await page.evaluate(() => ({ headings: [...document.querySelectorAll('h1,h2')].map(el => el.textContent), seen: window.__metrics.jobs, text: document.body.innerText.slice(0, 600) })) }));
    throw error;
  } finally { await context.close(); }
}
async function main() {
  const browser = await chromium.launch({ headless: true, channel: process.env.PERFORMANCE_BROWSER || 'msedge' });
  if (phase === 'verify') { try { await verifyRecovery(browser); } finally { await browser.close(); } return; }
  const result = { phase, browser: browser.version(), font: [], polling: [], naturalFont: null };
  try {
    for (let trial = 0; trial < 3; trial++) {
      const { context, page, fonts } = await setup(browser, 1800);
      await page.route('**/api/**', route => route.fulfill({ json: route.request().url().endsWith('/auth/me') ? identity : { items: [], total: 0, limit: 20, offset: 0 } }));
      await page.goto(base + '/incidents', { waitUntil: 'commit' });
      await page.getByRole('heading', { name: 'Incidents', exact: true }).waitFor();
      await page.waitForFunction(() => performance.getEntriesByType('resource').some(entry => entry.name.includes('fonts.googleapis.com')));
      await sleep(250);
      const sample = await page.evaluate(() => ({ fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null, lcp: window.__metrics.lcp, stylesheet: performance.getEntriesByType('resource').find(entry => entry.name.includes('fonts.googleapis.com'))?.duration, links: document.querySelectorAll('link[href*="fonts.googleapis.com"]').length }));
      result.font.push({ ...sample, requests: fonts.length }); console.log('font', trial + 1, JSON.stringify(sample));
      if (phase === 'after') { assert.ok(sample.fcp < 1800, 'first paint must not wait for the delayed font CSS'); assert.equal(sample.links, 1); }
      await context.close();
    }
    for (let trial = 0; trial < 3; trial++) {
      const { context, page } = await setup(browser, 0);
      const count = { jobs: 0, candidates: 0, session: 0, mutations: 0 }; const active = new Map(); let maxSameEndpoint = 0;
      await page.route('**/api/**', async route => {
        const url = new URL(route.request().url()); let body, delay = 0;
        if (url.pathname.endsWith('/auth/me')) body = identity;
        else if (url.pathname.endsWith('/jobs')) { const index = count.jobs++; delay = 80; const status = ['queued', 'running', 'succeeded'][Math.min(index, 2)]; body = { items: [{ job_id: 'J1', recording_id: 'R1', status, stage: 'PASS_1', progress: { done: index, total: 2 }, budget: { calls_used: index, max_calls: 10 }, partial_results: [], coverage: {}, error: null }], next_cursor: null }; }
        else if (url.pathname.endsWith('/candidates')) { count.candidates++; delay = 900; body = { items: [], next_cursor: null }; }
        else if (url.pathname.endsWith('/session')) { count.session++; delay = 1200; body = { subject: 'fixture', roles: ['Engineer'] }; }
        else { count.mutations++; body = {}; }
        const key = url.pathname; active.set(key, (active.get(key) || 0) + 1); maxSameEndpoint = Math.max(maxSameEndpoint, active.get(key));
        await sleep(delay); await route.fulfill({ json: body }); active.set(key, active.get(key) - 1);
      });
      await page.goto(base + '/recordings/R1', { waitUntil: 'commit' });
      await page.getByRole('heading', { name: 'Analysis: succeeded', exact: true }).waitFor();
      // Allow the last ancillary batch to settle, then another whole polling interval.
      await sleep(3400);
      const sample = await page.evaluate(() => ({ shown: window.__metrics.jobs, requests: performance.getEntriesByType('resource').filter(entry => new URL(entry.name).pathname.endsWith('/jobs')).map(entry => ({ end: entry.responseEnd, duration: entry.duration })) }));
      const latencies = sample.shown.map((item, index) => item.at - sample.requests[index].end);
      assert.deepEqual(sample.shown.map(item => item.text), ['Analysis: queued', 'Analysis: running', 'Analysis: succeeded']);
      assert.deepEqual(count, { jobs: 3, candidates: 3, session: 3, mutations: 0 }); assert.equal(maxSameEndpoint, 1);
      if (phase === 'after') assert.ok(Math.max(...latencies) < 300, 'job UI must not wait for 900/1200ms ancillary requests');
      result.polling.push({ count, maxSameEndpoint, latencyMs: latencies }); console.log('polling', trial + 1, JSON.stringify(result.polling.at(-1)));
      await context.close();
    }
    const { context, page, fonts } = await setup(browser, null);
    await page.route('**/api/**', route => route.fulfill({ json: route.request().url().endsWith('/auth/me') ? identity : { items: [], total: 0, limit: 20, offset: 0 } }));
    try {
      await page.goto(base + '/incidents', { waitUntil: 'commit' });
      await page.getByRole('heading', { name: 'Incidents', exact: true }).waitFor({ timeout: 15000 });
      await sleep(3000);
      result.naturalFont = await page.evaluate(() => ({ fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null, fontStatus: document.fonts.status, mulishAvailable: [...document.fonts].some(font => font.family === 'Mulish' && font.status === 'loaded'), cls: window.__metrics.cls, resources: performance.getEntriesByType('resource').filter(entry => /fonts\.(googleapis|gstatic)\.com/.test(entry.name)).map(entry => ({ url: entry.name, duration: entry.duration, bytes: entry.transferSize })) }));
    } catch (error) { result.naturalFont = { incomplete: error.message }; }
    result.naturalFont.network = fonts;
    if (phase === 'after' && result.naturalFont.mulishAvailable) {
      assert.equal(fonts.filter(entry => entry.url.includes('fonts.googleapis.com') && entry.status === 'finished').length, 1);
      assert.equal(fonts.filter(entry => entry.url.includes('fonts.gstatic.com') && entry.status === 'finished').length, 1, 'one variable font fetch for Latin UI text');
    }
    await context.close();
  } finally { await browser.close(); }
  const output = path.join(__dirname, '../test-results/performance'); fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, phase + '.json'), JSON.stringify(result, null, 2));
  console.log('RESULT', JSON.stringify(result));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
