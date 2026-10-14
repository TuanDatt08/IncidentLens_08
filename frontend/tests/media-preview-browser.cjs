const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const results = [];
  try {
    for (const width of [1440, 375]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const login = await context.request.post('http://127.0.0.1:3116/api/v1/auth/login', {
        headers: { Origin: 'http://127.0.0.1:3102' },
        data: { email: 'engineer@example.com', password: 'browser fixture password' },
      });
      assert.equal(login.status(), 200);
      const page = await context.newPage();
      const mediaResponses = [];
      let statusAttempts = 0;
      // Real backend HTTP, adapted by Playwright rather than the Next proxy.
      await page.route('**/api/**', async route => {
        if (route.request().url().endsWith('/video/preview/status')) {
          statusAttempts++;
          if (statusAttempts === 1) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'UNAVAILABLE', message: 'Temporary preview status failure' } }) });
          if (statusAttempts === 2) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ state: 'pending' }) });
        }
        const response = await route.fetch({ url: route.request().url().replace('127.0.0.1:3102', '127.0.0.1:3116') });
        if (route.request().url().includes('/video/preview')) mediaResponses.push({ status: response.status(), range: response.headers()['content-range'], type: response.headers()['content-type'] });
        await route.fulfill({ response });
      });
      await page.goto('http://127.0.0.1:3102/incidents/INC-PREVIEW');
      await page.getByRole('button', { name: 'Retry video preview', exact: true }).waitFor();
      assert.equal(await page.locator('video').count(), 0);
      await page.getByRole('button', { name: 'Retry video preview', exact: true }).focus();
      await page.keyboard.press('Enter');
      await page.getByText('Video preview is being prepared.', { exact: false }).waitFor();
      assert.equal(await page.locator('video').count(), 0);
      await page.getByRole('button', { name: 'Retry video preview', exact: true }).focus();
      await page.keyboard.press('Enter');
      await page.waitForFunction(() => document.querySelector('video')?.readyState >= 1);
      const src = await page.locator('video').getAttribute('src');
      assert.ok(src.endsWith('/video/preview'));
      await page.getByRole('button', { name: 'Play video', exact: true }).click();
      await page.waitForFunction(() => { const v = document.querySelector('video'); return v && !v.paused && v.currentTime > 0; });
      await page.getByRole('button', { name: 'Pause video', exact: true }).click();
      const slider = page.locator('input[type=range]');
      await slider.fill('5');
      await page.waitForFunction(() => Math.abs(document.querySelector('video').currentTime - 5) < 0.2);
      const state = await page.locator('video').evaluate(v => ({ paused: v.paused, currentTime: v.currentTime, duration: v.duration, mediaError: v.error?.code ?? null }));
      assert.equal(state.mediaError, null);
      assert.ok(mediaResponses.some(r => r.status === 206 && r.type === 'video/mp4'));
      results.push({ width, statusAttempts, errorPendingKeyboardRetry: true, src, ...state, mediaResponses });
      await page.unrouteAll({ behavior: 'wait' });
      await context.close();
    }
    fs.mkdirSync('frontend/test-results/media-preview', { recursive: true });
    fs.writeFileSync('frontend/test-results/media-preview/results.json', JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
