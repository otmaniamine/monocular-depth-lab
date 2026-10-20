// Optional local browser verification: NODE_PATH points to installed Playwright.
const {chromium} = require('playwright');
const {pathToFileURL} = require('url');
const path = require('path');
const assert = require('assert');
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1200,height:850}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const url = pathToFileURL(path.resolve('application/index.html')).href;
    await page.goto(url);
    await page.waitForFunction(() => [...document.images].every(i => i.complete && i.naturalWidth > 0));
    assert.equal(await page.locator('article').count(), 6);
    const links = await page.locator('a').evaluateAll(a => a.map(e=>e.href));
    const fs = require('fs');
    const {fileURLToPath} = require('url');
    for (const link of links) assert(fs.existsSync(fileURLToPath(link)), 'Missing link: '+link);
    await page.locator('video').evaluate(v=>v.load());
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
    const playback = await page.locator('video').evaluate(async v=>{
      v.muted=true; await v.play();
      await new Promise(resolve=>setTimeout(resolve,650));
      const result = {time:v.currentTime,width:v.videoWidth,height:v.videoHeight,error:v.error?.code||null};
      v.pause(); return result;
    });
    assert(playback.time>0 && playback.width>0 && playback.error===null, 'Video did not play');
    await page.screenshot({path:'results/application/galerie-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');
    await page.screenshot({path:'results/application/galerie-mobile.png',fullPage:true});
    await page.goto(pathToFileURL(path.resolve('application/01_navigation_routiere/video/index.html')).href);
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
    assert.equal(await page.locator('figure').count(),12);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({gallery:true,links:links.length,playback,mobile:true,videoViews:12,errors}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
