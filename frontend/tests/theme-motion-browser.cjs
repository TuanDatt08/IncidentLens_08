const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
(async () => {
 const browser = await chromium.launch({channel:'msedge',headless:true});
 const page = await browser.newPage(); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 const user={id:'ui-user',email:'fixture@example.com',display_name:'Workspace User',roles:['engineer','admin'],is_active:true,must_change_password:false};
 await page.route('**/api/v1/**',r=>{const p=new URL(r.request().url()).pathname;return r.fulfill({json:p.endsWith('/auth/me')?{user,csrf_token:'fixture'}:{items:[],total:0,limit:20,offset:0}})});
 await page.route('**/api/v2/**',r=>r.fulfill({json:new URL(r.request().url()).pathname.endsWith('/session')?{subject:user.id,roles:['Engineer']}:{items:[],next_cursor:null}}));
 fs.mkdirSync('.tmp/theme-motion',{recursive:true});
 for (const route of ['/', '/login','/incidents','/incidents/new','/recordings','/admin/users','/change-password','/recordings/REC-FIXTURE']) {
  await page.goto('http://127.0.0.1:3101'+route); await expect(page.locator('.theme-trigger')).toBeVisible();
  for(const mode of ['light','dark']) {
   if(await page.locator('html').getAttribute('data-theme')!==mode) await page.locator('.theme-trigger').click();
   await expect(page.locator('html')).toHaveAttribute('data-theme',mode);
   await expect(page.locator('input[type=color]')).toHaveCount(0);
   for(const width of [1440,768,390,320]) {
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    if(width===1440||width===390) await page.screenshot({path:'.tmp/theme-motion/'+(route.replaceAll('/','-')||'home')+'-'+mode+'-'+width+'.png'});
   }
  }
  console.log('PASS',route,'light/dark, 4 widths');
 }
 await page.locator('.theme-trigger').click(); await page.reload(); await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.emulateMedia({reducedMotion:'reduce'}); expect(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior)).toBe('auto');
 await page.goto('http://127.0.0.1:3101/'); await page.locator('.lp-mobile-menu summary').click(); await page.locator('.lp-mobile-menu a[href="/incidents"]').click(); await expect(page).toHaveURL(/incidents/);
 expect(errors).toEqual([]); console.log('PASS persistence, reduced motion, client navigation, no runtime errors');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
