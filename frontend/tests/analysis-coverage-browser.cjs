// Controlled API fixtures in a real production browser; not a live AI test.
const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const results = [];
const coverage = { state: 'available', time_basis: 'video_seconds', duration_s: 10, sampled_frame_count: 5, sampled_timestamps_s: [0, 2.5, 5, 7.5, 9.95], telemetry_alignment: 'UNKNOWN', limitations: ['Five sparse timestamps; gaps remain unknown.'] };
const report = detected => ({ incident_id: 'I1', incident_detected: detected, incident_type: detected ? 'COLLISION' : null, incident_window: detected ? { start: -1, critical: 0, end: 1 } : null, summary: detected ? 'Detected in supplied samples' : null, timeline: [], observations: [], key_factors: [], unknowns: [], evidence_ids: detected ? ['E1'] : [], review_status: 'DRAFT', version: 1, created_at: null, updated_at: null });
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    for (const width of [1440, 375]) for (const scenario of ['detected', 'none', 'missing', 'retry', 'processing-none']) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await context.newPage();
      let coverageCalls = 0, analyzeCalls = 0;
      await page.route('**/api/**', async route => {
        const url = route.request().url();
        if (url.endsWith('/auth/me')) return route.fulfill({ json: { csrf_token: 'fixture', user: { id: 'fixture', roles: ['engineer'], is_active: true, must_change_password: false, display_name: 'Fixture' } } });
        if (url.endsWith('/analyze')) { analyzeCalls++; return route.fulfill({ status: 500 }); }
        if (url.endsWith('/analysis-coverage')) {
          coverageCalls++;
          if (scenario === 'retry' && coverageCalls === 1) return route.fulfill({ status: 503, json: { error: { code: 'UNAVAILABLE', message: 'Coverage temporarily unavailable' } } });
          return route.fulfill({ json: scenario === 'missing' ? { ...coverage, state: 'unknown', duration_s: null, sampled_frame_count: null, sampled_timestamps_s: [], limitations: ['No completed report exists.'] } : coverage });
        }
        if (url.endsWith('/video/preview/status')) return route.fulfill({ json: { state: 'pending' } });
        if (url.endsWith('/I1')) return route.fulfill({ json: { incident_id: 'I1', processing_status: scenario === 'missing' ? 'FAILED' : 'COMPLETED', video_metadata: { duration: 10, width: 320, height: 240, collision_offset_in_video_s: 5 }, incident_record: null } });
        if (url.endsWith('/report')) return scenario === 'missing' ? route.fulfill({ status: 404, json: { error: { code: 'REPORT_NOT_FOUND', message: 'Insufficient analysis data' } } }) : route.fulfill({ json: report(scenario === 'detected') });
        if (url.endsWith('/evidence')) return route.fulfill({ json: { items: scenario === 'detected' ? [{ evidence_id: 'E1', kind: 'frame', time_range_s: [0, 0], sha256: 'a'.repeat(64), bytes: 1, media_type: 'image/jpeg', tier: 'core' }] : [] } });
        return route.fulfill({ json: { items: [] } });
      });
      await page.goto(`http://127.0.0.1:3102/incidents/I1${scenario === 'processing-none' ? '/processing' : ''}`);
      if (scenario === 'processing-none') {
        await page.getByText('Analysis needs review: no incident confirmed', { exact: true }).waitFor();
        await expect(page.getByText('Draft report ready', { exact: true })).toHaveCount(0);
        await expect(page.getByText('Open review to check telemetry conflicts, unresolved observations and coverage limits.')).toBeVisible();
      } else {
        if (scenario === 'retry') {
          await page.getByRole('button', { name: 'Retry analysis coverage', exact: true }).focus();
          await page.keyboard.press('Enter');
        }
        await page.getByRole('heading', { name: 'Analysis scope' }).waitFor();
        if (scenario === 'missing') {
          await expect(page.getByText('Analysis scope is unknown.', { exact: false })).toBeVisible();
          await expect(page.getByRole('heading', { name: 'No incident detected in inspected samples' })).toHaveCount(0);
          await expect(page.getByRole('button', { name: 'Retry report', exact: true })).toBeVisible();
        } else {
          await expect(page.getByText('5 frames inspected · 10.00s video')).toBeVisible();
          await expect(page.getByText('Sample-based analysis may miss events between frames or outside inspected windows.')).toBeVisible();
          if (scenario === 'detected') {
            await expect(page.getByRole('heading', { name: 'Incident Summary' })).toBeVisible();
            await expect(page.getByText('E1', { exact: true })).toBeVisible();
          } else {
            await expect(page.getByRole('heading', { name: 'No incident detected in inspected samples' })).toBeVisible();
            await expect(page.getByText('0 items', { exact: true })).toBeVisible();
            await expect(page.getByText('No incident evidence is available for this result.')).toBeVisible();
            await expect(page.getByText('Evidence will appear when Pass 2 has completed.')).toHaveCount(0);
          }
        }
      }
      const assertNoOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      if (!assertNoOverflow) throw new Error('Horizontal overflow');
      if (analyzeCalls) throw new Error('Viewing initiated AI');
      results.push({ width, scenario, pass: true, coverageCalls, analyzeCalls });
      await context.close();
    }
    fs.mkdirSync('frontend/test-results/analysis-coverage', { recursive: true });
    fs.writeFileSync('frontend/test-results/analysis-coverage/results.json', JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
