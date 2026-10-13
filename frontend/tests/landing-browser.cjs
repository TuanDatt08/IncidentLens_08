// Rendered Edge verification with synthetic API fixtures; not live API E2E.
const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.LANDING_BASE_URL || 'http://127.0.0.1:3000';
const output = path.resolve('.tmp/landing-final', `run-${new Date().toISOString().replace(/[:.]/g, '-')}`);
const results = [];
fs.mkdirSync(output, { recursive: true });

async function check(name, action) {
  if (process.env.LANDING_CHECK_FILTER && !name.includes(process.env.LANDING_CHECK_FILTER)) return;
  try { await action(); results.push({ name, pass: true }); }
  catch (error) { results.push({ name, pass: false, error: error.message }); }
}

async function inspect(page) {
  return page.evaluate(() => {
    const h = document.querySelector('h1'), scene = document.querySelector('.lp-source-video .lp-road');
    const s = getComputedStyle(h), r = h.getBoundingClientRect(), svg = scene?.getBoundingClientRect();
    return { overflow: document.documentElement.scrollWidth > innerWidth + 1,
      headingReadable: r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && Number(s.opacity) > .9 && parseFloat(s.fontSize) >= 30,
      sceneVisible: !!svg && svg.width > 50 && svg.height > 30 && (!!scene.querySelector('img')?.naturalWidth || scene.querySelectorAll('path').length > 10),
      shell: !!document.querySelector('.workspace-shell'), canvasCount: document.querySelectorAll('.lp-scene canvas').length, otherCanvas: document.querySelectorAll('canvas:not(.lp-scene canvas)').length };
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    for (const width of [1440, 768, 375, 320]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await context.newPage(); const errors = [], api = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => { if (new URL(r.url()).pathname.startsWith('/api/')) api.push(r.url()); });
      await check(`${width}: root and screenshots`, async () => {
        await page.goto(base, { waitUntil: 'domcontentloaded' }); await expect(page.locator('h1')).toBeVisible();
        await page.evaluate(() => document.fonts.ready);
        const data = await inspect(page);
        expect(data.overflow).toBe(false); expect(data.headingReadable).toBe(true); expect(data.sceneVisible).toBe(true); expect(data.shell).toBe(false); expect(data.canvasCount).toBeLessThanOrEqual(1); expect(data.otherCanvas).toBe(0);
        await page.screenshot({ path: path.join(output, `${width}-hero.png`) });
        // Reveal every below-fold section before saving the full-page capture.
        for (const section of await page.locator('[data-reveal]').all()) {
          // Decorative float need not be stable to reveal a section for its screenshot.
          await section.evaluate(el => el.scrollIntoView({ behavior: 'instant', block: 'center' }));
          await page.waitForTimeout(80);
        }
        await page.evaluate(() => scrollTo(0, 0));
        await page.screenshot({ path: path.join(output, `${width}-full.png`), fullPage: true });
      });
      await check(`${width}: evidence interaction`, async () => {
        const buttons = page.locator('.lp-demo-event-buttons button');
        for (const [index, time] of ['4.2', '6.8', '8.4'].entries()) {
          await buttons.nth(index).click(); await expect(buttons.nth(index)).toHaveAttribute('aria-pressed', 'true');
          expect(await page.locator('.lp-demo-event-buttons [aria-pressed="true"]').count()).toBe(1);
          await expect(page.locator('.lp-demo-inspector-copy')).toHaveAttribute('aria-live', 'polite');
          await expect(page.locator('.lp-demo-moment')).toContainText(time);
          await expect(page.locator('.lp-demo-evidence')).toContainText(`EV-0${index + 1}`);
          await expect(page.locator('.lp-demo-time')).toContainText(time);
        }
        await buttons.first().focus(); await page.keyboard.press('Tab');
        const focus = await page.evaluate(() => { const s = getComputedStyle(document.activeElement); return { tag: document.activeElement.tagName, outline: s.outlineStyle, width: s.outlineWidth, shadow: s.boxShadow }; });
        expect(focus.tag).toBe('BUTTON'); expect((focus.outline !== 'none' && parseFloat(focus.width) > 0) || focus.shadow !== 'none').toBeTruthy();
      });
      await check(`${width}: workflow CTA`, async () => {
        await page.locator('.lp-hero-actions a[href="#quy-trinh"]').click();
        await expect(page).toHaveURL(/#quy-trinh$/); await expect(page.locator('#quy-trinh')).toBeFocused();
      });
      if (width <= 768) await check(`${width}: keyboard mobile menu`, async () => {
        const summary = page.locator('.lp-mobile-menu summary'), details = page.locator('.lp-mobile-menu');
        await summary.focus(); await page.keyboard.press('Enter'); await expect(details).toHaveAttribute('open', '');
        await page.keyboard.press('Tab'); await page.keyboard.press('Escape');
        expect(await details.evaluate(el => el.open)).toBe(false); await expect(summary).toBeFocused();
        await page.keyboard.press('Enter'); await details.locator('a[href="#trai-nghiem"]').click();
        expect(await details.evaluate(el => el.open)).toBe(false); await expect(page.locator('#trai-nghiem')).toBeFocused();
      });
      await check(`${width}: landing API isolation and page errors`, async () => { expect(api).toEqual([]); expect(errors).toEqual([]); });
      await context.close();
    }

    await check('375: reduced motion and pointer static', async () => {
      const context = await browser.newContext({ viewport: { width: 375, height: 900 }, reducedMotion: 'reduce' });
      const page = await context.newPage(); await page.goto(base, { waitUntil: 'domcontentloaded' });
      expect((await inspect(page)).headingReadable).toBe(true);
      const motion = await page.locator('.lp-core-orbit, .lp-signal-flow').evaluateAll(nodes => nodes.map(el => getComputedStyle(el).animationName));
      expect(motion.every(name => name === 'none')).toBe(true);
      await page.locator('.lp-scene').scrollIntoViewIfNeeded(); const box = await page.locator('.lp-scene').boundingBox();
      await page.mouse.move(box.x + box.width * .9, box.y + box.height * .8);
      const tilt = await page.locator('.lp-scene').evaluate(el => [el.style.getPropertyValue('--scene-x'), el.style.getPropertyValue('--scene-y')]);
      expect(tilt.every(value => value === '' || value === '0deg')).toBe(true);
      await page.screenshot({ path: path.join(output, '375-reduced-motion.png'), fullPage: true }); await context.close();
    });
    await check('375: JavaScript disabled fallback', async () => {
      const context = await browser.newContext({ viewport: { width: 375, height: 900 }, javaScriptEnabled: false });
      const page = await context.newPage(); await page.goto(base); await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('.lp-hero-actions a[href="/incidents"]')).toBeVisible();
      expect((await inspect(page)).sceneVisible).toBe(true);
      const details = page.locator('.lp-mobile-menu'); await details.locator('summary').click();
      expect(await details.evaluate(el => el.open)).toBe(true);
      await page.screenshot({ path: path.join(output, '375-no-javascript.png'), fullPage: true }); await context.close();
    });
    await check('CTA /incidents preserves workspace (API fixture only)', async () => {
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } }); const page = await context.newPage();
      await page.route('**/api/**', route => {
        const url = new URL(route.request().url());
        if (url.pathname === '/api/v1/auth/me') return route.fulfill({ json: { csrf_token: 'fixture', user: { id: 'fixture', email: 'fixture@example.com', display_name: 'Fixture', roles: ['engineer'], is_active: true, must_change_password: false } } });
        if (url.pathname === '/api/v1/incidents') return route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } });
        return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Fixture not configured' } } });
      });
      await page.goto(base); const cta = page.locator('.lp-hero-actions a[href="/incidents"]'); await expect(cta).toHaveAttribute('href', '/incidents');
      await cta.click(); await expect(page).toHaveURL(/\/incidents$/); await expect(page.locator('.workspace-shell, body > div.min-h-screen').first()).toBeVisible();
      await page.screenshot({ path: path.join(output, 'workspace-fixture.png') }); await context.close();
    });
    if (process.env.LANDING_AUTH_BASE_URL) {
      for (const authenticated of [false, true]) {
        await check(`Auth-enabled: ${authenticated ? 'authenticated workspace' : 'public root and anonymous login redirect'} (synthetic auth fixture only)`, async () => {
          const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
          try {
            const page = await context.newPage(), requests = [], errors = [];
            page.on('pageerror', error => errors.push(error.message));
            page.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) requests.push(request.url()); });
            await page.route('**/api/**', route => {
              const url = new URL(route.request().url());
              if (url.pathname === '/api/v1/auth/me') {
                if (!authenticated) return route.fulfill({ status: 401, json: { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Synthetic anonymous session' } } });
                return route.fulfill({ json: { csrf_token: 'synthetic-auth-fixture', user: { id: 'fixture', email: 'fixture@example.com', display_name: 'Fixture', roles: ['engineer'], is_active: true, must_change_password: false } } });
              }
              if (url.pathname === '/api/v1/incidents') return route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } });
              return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Fixture not configured' } } });
            });
            await page.goto(process.env.LANDING_AUTH_BASE_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
            await expect(page.locator('h1')).toBeVisible();
            await expect(page.locator('h1')).toHaveAttribute('id', 'lp-title');
            // Interaction waits for React event handlers; root stays isolated from session APIs.
            await expect(async () => {
              await page.locator('.lp-demo-event-buttons button').first().click();
              await expect(page.locator('.lp-demo-event-buttons button').first()).toHaveAttribute('aria-pressed', 'true', { timeout: 1000 });
            }).toPass({ timeout: 15000 });
            expect(await page.locator('.workspace-shell').count()).toBe(0); expect(requests).toEqual([]);
            await page.locator('.lp-hero-actions a[href="/incidents"]').click();
            if (authenticated) {
              await expect(page).toHaveURL(/\/incidents$/); await expect(page.locator('.workspace-shell')).toBeVisible();
            } else {
              await expect(page).toHaveURL(/\/login\?returnTo=%2Fincidents$/, { timeout: 30000 });
              await expect(page.locator('input[type="password"]')).toBeVisible();
            }
            expect(requests.some(url => new URL(url).pathname === '/api/v1/auth/me')).toBe(true);
            expect(errors).toEqual([]);
            await page.screenshot({ path: path.join(output, `auth-${authenticated ? 'workspace' : 'login'}-fixture.png`) });
          } finally { await context.close(); }
        });
      }
    }
  } finally {
    await browser.close(); fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({ base, verification: 'Rendered Edge UI with synthetic fixtures, not live API integration', results }, null, 2));
  }
  const failures = results.filter(r => !r.pass);
  console.log(`Landing browser: ${results.length - failures.length}/${results.length} checks passed.`);
  console.log(`Artifacts: ${output}`);
  for (const failure of failures) console.error(`${failure.name}: ${failure.error}`);
  if (failures.length) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exitCode = 1; });
