// Rendered Edge UI evidence; synthetic product data, no live backend verification.
const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const base = process.env.LANDING_BASE_URL || 'http://127.0.0.1:3000';
const output = path.resolve('.tmp/galaxy-final', `run-${new Date().toISOString().replace(/[:.]/g, '-')}`);
fs.mkdirSync(output, { recursive: true });
const results = [], observations = [];
async function check(name, run) { if(process.env.GALAXY_CHECK_FILTER&&!name.includes(process.env.GALAXY_CHECK_FILTER))return;try { await run(); results.push({name, pass:true}); } catch(e) { results.push({name, pass:false, error:e.message}); } }
async function snapshot(page) {
  return page.evaluate(() => ({ visibility:document.visibilityState, frame:Number(document.querySelector('.lp-scene canvas')?.dataset.frame || 0), canvases:document.querySelectorAll('canvas').length, orbit:[...document.querySelectorAll('.lp-core-orbit')].map(el => getComputedStyle(el).transform), overflow:document.documentElement.scrollWidth > innerWidth + 1 }));
}
async function load(page) { await page.goto(base, {waitUntil:'domcontentloaded'}); await expect(page.locator('h1')).toBeVisible(); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(1200); }
async function panels(page){return page.evaluate(()=>{const s=document.querySelector('.lp-scene').getBoundingClientRect(),t=document.querySelector('.lp-hero h1').getBoundingClientRect();return [...document.querySelectorAll('.lp-scene>.lp-source')].map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,inScene:r.left>=s.left-2&&r.right<=s.right+2&&r.top>=s.top-2&&r.bottom<=s.bottom+2,overText:r.left<t.right&&r.right>t.left&&r.top<t.bottom&&r.bottom>t.top,transform:getComputedStyle(el).transform};});});}
async function satellites(page){return page.locator('.lp-space-satellite').evaluateAll(nodes=>nodes.filter(el=>getComputedStyle(el).display!=='none').map(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return {x:r.x,y:r.y,transform:s.transform,background:s.backgroundImage,border:s.borderTopStyle,hidden:el.getAttribute('aria-hidden')};}));}
async function main() {
  const browser = await chromium.launch({headless:true, channel:'msedge'});
  try {
    for (const width of [1440,375,320]) {
      const context = await browser.newContext({viewport:{width,height:900},hasTouch:width<768,deviceScaleFactor:width<768?2:1}), page = await context.newPage();
      const errors=[], api=[]; page.on('pageerror',e=>errors.push(e.message)); page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))api.push(r.url());});
      await load(page);
      await check(`${width}: visible cosmic satellite motion and semantics`,async()=>{
        await page.locator('.lp-scene').scrollIntoViewIfNeeded();const a=await satellites(page);expect(a.length).toBe(width<=480?4:6);expect(a.every(p=>p.hidden==='true'&&(p.background!=='none'||p.border!=='none'))).toBe(true);await page.waitForTimeout(2100);const b=await satellites(page);const distances=a.map((p,i)=>Math.hypot(p.x-b[i].x,p.y-b[i].y));expect(distances.every(d=>d>5)).toBe(true);observations.push({width,cosmicSatellites:{count:a.length,distances}});
      });
      await check(`${width}: local dashcam and meaningful satellite orbit`,async()=>{
        await page.locator('.lp-scene').scrollIntoViewIfNeeded();await page.waitForTimeout(200);
        const photo=await page.locator('.lp-source-video img').evaluate(el=>({loaded:el.complete&&el.naturalWidth>0,src:el.getAttribute('src')}));expect(photo.loaded).toBe(true);expect(photo.src).toBe('/landing/dashcam-demo-v2.webp');
        const a=await panels(page);await page.waitForTimeout(3100);const b=await panels(page);const distances=a.map((p,i)=>Math.hypot(p.x-b[i].x,p.y-b[i].y));observations.push({width,satelliteOrbit:{a,b,distances}});expect(distances.every(d=>d>15)).toBe(true);expect([...a,...b].every(p=>p.inScene&&!p.overText)).toBe(true);
        for(let i=0;i<6;i++){const state=await panels(page);expect(state.every(p=>p.inScene&&!p.overText)).toBe(true);await page.screenshot({path:path.join(output,`${width}-satellite-orbit-${i}.png`)});await page.waitForTimeout(3000);}
      });
      if(width===1440) observations.push({contrast:await page.evaluate(()=>{
        const parse=color=>{const n=color.match(/[\d.]+/g)?.map(Number)||[];return n.length>=3?n.slice(0,3):null;};
        const luminance=rgb=>rgb.map(n=>{const s=n/255;return s<=.04045?s/12.92:((s+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
        return ['.lp-hero h1','.lp-hero-description','.lp-hero-actions .lp-button'].map(selector=>{
          const el=document.querySelector(selector);if(!el)return {selector,missing:true};const color=getComputedStyle(el).color, fg=parse(color), bg=[5,6,17];
          let parent=el,background='rgb(5, 6, 17)';while(parent){const s=getComputedStyle(parent),parsed=parse(s.backgroundColor),alpha=(s.backgroundColor.match(/[\d.]+/g)||[])[3];if(parsed&&(!alpha||Number(alpha)===1)){bg.splice(0,3,...parsed);background=s.backgroundColor;break;}parent=parent.parentElement;}
          const a=luminance(fg||[244,246,255]),b=luminance(bg),image=getComputedStyle(el).backgroundImage,stops=(image.match(/rgba?\([^)]+\)/g)||[]).map(parse).filter(Boolean);return {selector,color,quietSolidBackground:background,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),gradientStopRatios:stops.map(rgb=>{const l=luminance(rgb);return (Math.max(a,l)+.05)/(Math.min(a,l)+.05);}),limitation:'Gradient stop and solid backdrop computations; surrounding glow needs screenshot review.'};
        });
      })});
      await check(`${width}: actual hero frames and overflow`,async()=>{
        await page.locator('.lp-scene').scrollIntoViewIfNeeded(); await page.waitForTimeout(350);
        const a=await snapshot(page), imageA=await page.screenshot({path:path.join(output,`${width}-frame-a.png`)});
        await page.waitForTimeout(1000);
        const b=await snapshot(page), imageB=await page.screenshot({path:path.join(output,`${width}-frame-b.png`)});
        const changed=crypto.createHash('sha256').update(imageA).digest('hex')!==crypto.createHash('sha256').update(imageB).digest('hex');
        observations.push({width,a,b,screenshotChanged:changed});
        expect(a.canvases).toBeLessThanOrEqual(1); expect(a.overflow||b.overflow).toBe(false);
        expect(b.frame>a.frame || a.orbit.some((t,i)=>t!==b.orbit[i])).toBe(true); expect(changed).toBe(true);
      });
      await check(`${width}: sampled live renderer cadence and pixel cap`,async()=>{
        const cadence=await page.evaluate(()=>new Promise(resolve=>{
          const canvas=document.querySelector('.lp-scene canvas'),bounds=canvas?.getBoundingClientRect(),samples=[];let start,previous=Number(canvas?.dataset.frame||0),lastChange;
          function tick(time){start??=time;const frame=Number(canvas?.dataset.frame||0);if(frame!==previous){samples.push({time:time-start,frame,interval:lastChange===undefined?null:time-lastChange});lastChange=time;previous=frame;}if(time-start<3000)requestAnimationFrame(tick);else resolve({elapsed:time-start,samples,coarse:matchMedia('(pointer:coarse)').matches,devicePixelRatio,renderPixelRatio:bounds&&bounds.width?canvas.width/bounds.width:0});}requestAnimationFrame(tick);
        }));
        observations.push({width,cadence});expect(cadence.samples.length).toBeGreaterThan(10);expect(cadence.renderPixelRatio).toBeLessThanOrEqual(cadence.coarse?1.02:1.27);
        if(width===1440)for(let i=0;i<6;i++){await page.screenshot({path:path.join(output,`motion-sequence-${i}.png`)});await page.waitForTimeout(500);}
      });
      await check(`${width}: four workflow stages`,async()=>{
        const buttons=page.locator('.lp-workflow-button'); await expect(buttons).toHaveCount(4);
        const copies=[];
        for(let i=0;i<4;i++) { await buttons.nth(i).click(); await expect(buttons.nth(i)).toHaveAttribute('aria-pressed','true'); expect(await page.locator('.lp-workflow-button[aria-pressed="true"]').count()).toBe(1); copies.push(await page.locator('.lp-workflow-copy').innerText()); }
        expect(new Set(copies).size).toBe(4); expect((await snapshot(page)).overflow).toBe(false);
      });
      await check(`${width}: scroll handoff`,async()=>{
        const handoff=page.locator('.lp-handoff'); await expect(handoff).toHaveCount(1);
        const box=await handoff.evaluate(el=>({top:el.getBoundingClientRect().top+scrollY,height:el.getBoundingClientRect().height}));
        await page.evaluate(y=>scrollTo({top:y,behavior:'instant'}),Math.max(0,box.top-600)); await page.waitForTimeout(600);
        const a=await handoff.evaluate(el=>getComputedStyle(el).getPropertyValue('--handoff-progress'));
        await page.evaluate(y=>scrollTo({top:y,behavior:'instant'}),box.top+box.height/2); await page.waitForTimeout(600);
        const b=await handoff.evaluate(el=>getComputedStyle(el).getPropertyValue('--handoff-progress'));
        observations.push({width,handoffProgress:[a,b]}); expect(a).not.toBe(b); expect((await snapshot(page)).overflow).toBe(false);
        const clipping=await handoff.evaluate(el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {overflow:s.overflowY,sectionHeight:r.height,contentHeight:el.scrollHeight,children:[...el.querySelectorAll('h2,p,.lp-handoff-tags')].map(child=>{const c=child.getBoundingClientRect();return {text:child.textContent,bottom:c.bottom-r.top};})};});observations.push({width,handoffClipping:clipping});if(clipping.overflow==='hidden'||clipping.overflow==='clip')expect(clipping.children.every(child=>child.bottom<=clipping.sectionHeight+1)).toBe(true);
        await page.screenshot({path:path.join(output,`${width}-handoff.png`)});
      });
      await check(`${width}: offscreen renderer pauses`,async()=>{
        await page.locator('.lp-footer').scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
        const a=await snapshot(page); await page.waitForTimeout(900); const b=await snapshot(page);
        observations.push({width,offscreenFrames:[a.frame,b.frame]}); expect(b.frame).toBe(a.frame);
        const pa=await panels(page);await page.waitForTimeout(700);const pb=await panels(page);expect(pa.map(p=>p.transform)).toEqual(pb.map(p=>p.transform));
        const sa=await satellites(page);await page.waitForTimeout(700);expect(sa.map(s=>s.transform)).toEqual((await satellites(page)).map(s=>s.transform));
      });
      await check(`${width}: root API isolation`,async()=>{expect(errors).toEqual([]);expect(api).toEqual([]);});
      await check(`${width}: ambient artwork active and offscreen pause`,async()=>{
        for(const [section,art,name] of [['.lp-workflow-console','.lp-workflow-illustration','workflow'],['.lp-feature-layout','.lp-mini-list','capabilities']]){
          await page.locator(section).scrollIntoViewIfNeeded();await page.waitForTimeout(350);const read=()=>page.locator(art).evaluate(el=>{const s=getComputedStyle(el);return {translate:s.translate,rotate:s.rotate,play:s.animationPlayState,animation:s.animationName};});const a=await read();await page.waitForTimeout(2100);const b=await read();expect(a.translate!==b.translate||a.rotate!==b.rotate).toBe(true);await page.screenshot({path:path.join(output,`${width}-${name}-ambient.png`)});await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await expect(page.locator(section)).toHaveAttribute('data-space-active','false');await page.waitForTimeout(300);const c=await read();await page.waitForTimeout(700);const d=await read();expect(c.translate).toBe(d.translate);expect(c.rotate).toBe(d.rotate);expect(c.play).toBe('paused');observations.push({width,ambient:name,a,b,offscreen:c});
        }
      });
      await context.close();
    }
    for(const reduced of [false,true]) {
      const context=await browser.newContext({viewport:{width:1440,height:900}, reducedMotion:reduced?'reduce':'no-preference'});
      if(!reduced) await context.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){if(String(kind).startsWith('webgl')||kind==='experimental-webgl')return null;return original.call(this,kind,...args);};});
      const page=await context.newPage(),errors=[],api=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))api.push(r.url());}); await load(page);
      await check(reduced?'Reduced motion static composition':'Forced WebGL-unavailable fallback',async()=>{
        await page.locator('.lp-scene').scrollIntoViewIfNeeded(); await expect(page.locator('.lp-source-video .lp-road')).toBeVisible();
        const a=await snapshot(page);await page.waitForTimeout(1000);const b=await snapshot(page);
        if(reduced){expect(b.frame-a.frame).toBeLessThanOrEqual(1);expect(a.orbit).toEqual(b.orbit); const animation=await page.locator('.lp-core-orbit').evaluateAll(els=>els.map(el=>getComputedStyle(el).animationName));expect(animation.every(n=>n==='none')).toBe(true);const pa=await panels(page),sa=await satellites(page);await page.waitForTimeout(700);expect(pa.map(p=>p.transform)).toEqual((await panels(page)).map(p=>p.transform));expect(sa.map(s=>s.transform)).toEqual((await satellites(page)).map(s=>s.transform));const ambient=await page.locator('.lp-workflow-illustration,.lp-mini-list,.lp-feature-chain').evaluateAll(nodes=>nodes.map(el=>getComputedStyle(el).animationName));expect(ambient.every(n=>n==='none')).toBe(true);}
        expect(a.overflow).toBe(false);expect(errors).toEqual([]);expect(api).toEqual([]);
        observations.push({mode:reduced?'reduced':'fallback',a,b});await page.screenshot({path:path.join(output,reduced?'reduced-motion.png':'webgl-fallback.png'),fullPage:true});
      }); await context.close();
    }
    observations.push({tabHidden:'Not tested: no genuine tab-visibility transition asserted in headless Edge. Static review required.',motionLimit:'Frame changes establish animation activity, not frame-time smoothness or GPU performance.'});
  } finally { await browser.close();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({base,results,observations},null,2)); }
  console.log(`Galaxy: ${results.filter(r=>r.pass).length}/${results.length} checks passed. Artifacts: ${output}`);for(const r of results.filter(r=>!r.pass))console.error(`${r.name}: ${r.error}`);if(results.some(r=>!r.pass))process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=1;});
