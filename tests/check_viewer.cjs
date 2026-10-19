// Optional browser QA: npm install playwright, then node tests/check_viewer.cjs.
const { chromium } = require('playwright');
const path = require('path');
const { pathToFileURL } = require('url');
const assert = require('assert');
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage({viewport:{width:1100,height:820}});
    const errors=[]; page.on('pageerror',e=>errors.push(e.message));
    const file = process.argv[2] || 'results/3d/demo01_outdoor.html';
    await page.goto(pathToFileURL(path.resolve(file)).href);
    const root = page.locator('#depth-cloud-viewer');
    await root.waitFor();
    await page.waitForFunction(()=>document.querySelector('#depth-cloud-viewer').dataset.ready==='true');
    const count=+await root.getAttribute('data-points');assert(count>1000);
    const rendered = await page.locator('canvas').evaluate(canvas=>{
      const gl=canvas.getContext('webgl');const pixels=new Uint8Array(canvas.width*canvas.height*4);
      gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
      let different=0;for(let i=4;i<pixels.length;i+=4)if(pixels[i]!==pixels[0]||pixels[i+1]!==pixels[1]||pixels[i+2]!==pixels[2])different++;
      return different;
    });assert(rendered>1000,'Point cloud did not render');
    await page.getByRole('button',{name:'Vue oblique',exact:true}).click();
    assert.equal(await root.getAttribute('data-yaw'),'0.5500');
    await page.screenshot({path:'results/3d/viewer-oblique.png',fullPage:true});
    await page.getByRole('button',{name:'Profil',exact:true}).click();
    await page.screenshot({path:'results/3d/viewer-profile.png',fullPage:true});
    const before=await root.getAttribute('data-yaw');const box=await page.locator('canvas').boundingBox();
    await page.mouse.move(box.x+200,box.y+150);await page.mouse.down();await page.mouse.move(box.x+260,box.y+165);await page.mouse.up();
    assert.notEqual(await root.getAttribute('data-yaw'),before);
    const zoom=await page.getByRole('slider',{name:'Zoom',exact:true}).inputValue();await page.mouse.wheel(0,-100);
    assert.notEqual(await page.getByRole('slider',{name:'Zoom',exact:true}).inputValue(),zoom);
    await page.setViewportSize({width:360,height:740});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile page overflows');
    await page.screenshot({path:'results/3d/viewer-mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({points:count,renderedPixels:rendered,rotation:true,zoom:true,mobile:true,errors}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
