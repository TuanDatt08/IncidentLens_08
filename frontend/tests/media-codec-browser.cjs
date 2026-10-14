const { chromium } = require('playwright');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

// Local decoding probe; API authorization/Range is checked separately.
(async () => {
  const file = path.resolve(process.argv[2]);
  const server = http.createServer((req, res) => {
    if (req.url === '/video') {
      const size = fs.statSync(file).size;
      const match = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range || '');
      const start = match ? Number(match[1]) : 0;
      const end = match && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
      res.writeHead(match ? 206 : 200, {
        'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes',
        'Content-Length': end - start + 1,
        ...(match ? { 'Content-Range': `bytes ${start}-${end}/${size}` } : {}),
      });
      fs.createReadStream(file, { start, end }).pipe(res);
    } else { res.setHeader('Content-Type', 'text/html'); res.end('<video muted controls src="/video"></video>'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    for (const width of [1440, 375]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(`http://127.0.0.1:${server.address().port}`);
      const result = await page.evaluate(async () => {
        const video = document.querySelector('video');
        try {
          await video.play();
          await new Promise(resolve => setTimeout(resolve, 400));
          video.currentTime = 5;
          await new Promise((resolve, reject) => {
            video.addEventListener('seeked', resolve, { once: true });
            setTimeout(() => reject(new Error('seek timeout')), 5000);
          });
          return { playing: !video.paused, currentTime: video.currentTime, duration: video.duration };
        } catch (error) {
          return { playing: false, error: error.name, message: error.message, mediaError: video.error?.code };
        }
      });
      console.log(JSON.stringify({ width, ...result }));
      await page.close();
    }
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
