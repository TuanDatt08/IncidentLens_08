// Rendered Chromium checks with API fixtures, not backend integration.
// 200% uses a half-width CSS viewport and deviceScaleFactor 2 to reproduce reflow.
const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const id = 'REC-' + '1234567890abcdef'.repeat(4).slice(0, 60);
const cases = [ ['320', 320, 1], ['375', 375, 1], ['tablet', 768, 1], ['small-desktop', 1024, 1], ['desktop', 1440, 1], ['desktop-200-percent', 720, 2] ];
async function main() {
  const browser = await chromium.launch({ headless: true, channel: process.env.RESPONSIVE_BROWSER || 'msedge' });
  const failures = [];
  const output = path.join(__dirname, '../test-results/responsive'); fs.mkdirSync(output, { recursive: true });
  try {
    for (const [name, width, scale] of cases) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: scale });
      const page = await context.newPage();
      await page.route('**/api/**', route => {
        const url = new URL(route.request().url()); let body;
        if (url.pathname === '/api/v1/auth/me') body = { csrf_token: 'fixture', user: { id: 'fixture', email: 'long-email-' + 'a'.repeat(64) + '@example.com', display_name: 'Long Display Name ' + 'b'.repeat(64), roles: ['engineer', 'admin'], is_active: true, must_change_password: false } };
        else if (url.pathname === '/api/v1/incidents') body = { items: [{ incident_id: id.replace('REC', 'INC'), processing_status: 'COMPLETED', created_at: '2026-10-11T00:00:00Z', incident_record: { scenario: 'long_scenario_' + 'c'.repeat(80) } }], total: 40, limit: 20, offset: 0 };
        else if (url.pathname === '/api/v2/session') body = { subject: 'fixture', roles: ['Engineer'] };
        else if (url.pathname === '/api/v2/recordings') body = { items: [{ recording_id: id, duration_s: 1234 }], next_cursor: 'next' };
        else return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Fixture not configured' } } });
        return route.fulfill({ json: body });
      });
      for (const route of ['/incidents', '/recordings']) {
        await page.goto((process.env.RESPONSIVE_BASE_URL || 'http://127.0.0.1:3102') + route);
        await page.getByText(route === '/incidents' ? id.replace('REC', 'INC') : id, { exact: true }).filter({ visible: true }).first().waitFor();
        await page.evaluate(() => document.fonts.ready);
        const inspect = async (menu = false) => {
          const result = await page.evaluate(() => {
            const root = document.documentElement;
            const header = document.querySelector('header').getBoundingClientRect();
            const nav = document.querySelector('.workspace-sidebar-nav').getBoundingClientRect();
            const main = document.querySelector('main').getBoundingClientRect();
            const headerOverlap = main.top < header.bottom - 1;
            const clipped = [...document.querySelectorAll('main a, main td, main [role="group"], .workspace-sidebar-nav')].filter(el => el.getBoundingClientRect().width && el.scrollWidth > el.clientWidth + 2).map(el => el.textContent.trim().slice(0, 50));
            const menu = document.querySelector('header details[open]');
            const controls = [...document.querySelectorAll('.workspace-sidebar a, header a, header summary, header button, main button, main td:last-child a, main a[href^="/recordings/"]')].filter(el => {
              const details = el.closest('details');
              if (details && !details.open && el.tagName !== 'SUMMARY') return false;
              if (menu && !menu.contains(el)) return false; // A popup intentionally overlays the underlying page.
              return el.getBoundingClientRect().width && !el.disabled;
            });
            const blocked = controls.filter(el => { const r = el.getBoundingClientRect(); if (r.top < 0 || r.bottom > innerHeight) return false; const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return !el.contains(top); }).map(el => el.textContent.trim().slice(0, 30));
            const small = controls.filter(el => el.getBoundingClientRect().height < 40).map(el => el.textContent.trim().slice(0, 30));
            return { width: root.clientWidth, scroll: root.scrollWidth, clipped, blocked, small, headerOverlap };
          });
          const label = `${name} ${route}${menu ? ' menu' : ''}`;
          console.log(label, JSON.stringify(result));
          if (result.scroll > result.width + 1 || result.clipped.length || result.blocked.length || result.small.length || result.headerOverlap) failures.push({ label, ...result });
          await page.screenshot({ path: path.join(output, `${name}-${route.slice(1)}${menu ? '-menu' : ''}.png`), fullPage: true });
        };
        await inspect();
        await page.getByRole('button', { name: 'Account menu' }).focus(); await page.keyboard.press('Enter'); await inspect(true);
        await page.keyboard.press('Escape');
        await assert.equal(await page.getByRole('button', { name: 'Account menu' }).evaluate(el => el.parentElement.open), false);
        if (route === '/incidents') { await page.getByRole('button', { name: /^All \d+$/, exact: true }).focus(); await page.keyboard.press('Enter'); }
      }
      await context.close();
    }
    assert.deepEqual(failures, [], 'overflow, clipped content, blocked or undersized controls');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
