// Focused packaged startup: isolated profile/APPDATA, no account or owner save.
import { chromium } from '../web/node_modules/@playwright/test/index.mjs';
import { spawn, execFileSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const VERSION=JSON.parse(readFileSync(new URL('../companion/launcher/package.json',import.meta.url),'utf8')).version;
// Optional pre-deploy web fixture: run the real built frontend at its expected
// origin without depending on public connectivity. Never changes the package.
const [exe, output, webDist] = process.argv.slice(2);
assert(exe && output);
await mkdir(path.join(output,'appdata'),{recursive:true});
const env={...process.env,APPDATA:path.join(output,'appdata'),POKEAPP_LAUNCHER_PROFILE:path.join(output,'profile'),POKEAPP_LAUNCHER_HEADLESS_TEST:'1'};
delete env.ELECTRON_RUN_AS_NODE;
const child=spawn(exe,['--remote-debugging-port=9343'],{env,windowsHide:true,stdio:'ignore'});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let browser;
const report={status:'RUNNING',version:VERSION,web_source:webDist?'isolated built frontend':'public origin',checks:[]};
try {
  for(let n=0;n<60&&!browser;n++) {
    await pause(500);
    browser=await chromium.connectOverCDP('http://127.0.0.1:9343').catch(()=>null);
  }
  assert(browser,'packaged startup');
  if(webDist) {
    const root=path.resolve(webDist);
    await browser.contexts()[0].route('https://pokeapp-web.pokeapp-v2.workers.dev/**',async route=>{
      const requested=path.resolve(root,'.'+decodeURIComponent(new URL(route.request().url()).pathname));
      assert(requested===root||requested.startsWith(root+path.sep),'fixture stays inside built web');
      const file=/\.[a-z0-9]+$/i.test(requested)?requested:path.join(root,'index.html');
      const ext=path.extname(file);
      const type={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.woff2':'font/woff2','.svg':'image/svg+xml'}[ext]||'application/octet-stream';
      await route.fulfill({status:200,body:readFileSync(file),contentType:type});
    });
  }
  let shell;
  for(let n=0;n<60&&!shell;n++) {
    shell=browser.contexts().flatMap(c=>c.pages()).find(p=>p.url().includes('shell=unified'));
    if(!shell) await pause(500);
  }
  assert(shell,'native shell');
  await shell.waitForFunction(()=>typeof window.launcher?.state==='function');
  // 0.26.7: a core that is still starting is refused at once with its status
  // (the hub shows it); the state arrives as soon as the core is READY.
  let state;
  for(let n=0;n<80;n++) {
    state=await shell.evaluate(()=>window.launcher.state()).catch(()=>null);
    if(state?.local_status) break;
    await pause(250);
  }
  const core=await shell.evaluate(()=>window.launcher.core());
  assert(core?.status==='READY'&&core.starts===1,'supervised core READY on its first start');
  assert(state?.local_status,'packaged Python core answers IPC');
  assert(!state.principal,'no real account');
  assert(!state.selected_save,'no owner save selected');
  if(webDist) for(const page of browser.contexts()[0].pages()) {
    if(page!==shell && (page.url().startsWith('https://pokeapp-web.')||page.url().startsWith('chrome-error://')))
      await page.goto('https://pokeapp-web.pokeapp-v2.workers.dev/',{waitUntil:'domcontentloaded'});
  }
  const web=browser.contexts().flatMap(c=>c.pages()).find(p=>p.url().startsWith('https://pokeapp-web.'));
  assert(web,'official web origin');
  // Read the DOM directly: on this machine Playwright's frame tracking can wait
  // forever on the Launcher's intercepted (never committed) session navigation.
  let login=false;
  for(let n=0;n<60&&!login;n++) {
    login=await web.evaluate(()=>[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='Entrar a PokeApp'&&b.offsetParent!==null)).catch(()=>false);
    if(!login) await pause(500);
  }
  assert(login,'web login form');
  const boundary=await web.evaluate(v=>({node:typeof require,bridge:typeof window.launcher,version:navigator.userAgent.includes('PokeAppLauncher/'+v)}),VERSION);
  assert(boundary.node==='undefined'&&boundary.bridge==='undefined'&&boundary.version,'web IPC boundary/version');
  report.checks=['Packaged startup','Real core IPC','Supervised core READY','Isolated empty profile',webDist?'Built frontend login at intercepted official origin':'Official web login','No web Node/IPC bridge',VERSION+' user agent'];
  // Fail only the disposable child's idle core, then wait for its supervisor.
  // Never enumerate or stop another Launcher, an owner's profile or a writer.
  const ownedCore=JSON.parse(execFileSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',
    `$rows=@(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq ${child.pid} -and $_.Name -eq 'PokeApp.Core.exe' }); ConvertTo-Json -InputObject $rows -Compress`],
    {encoding:'utf8',windowsHide:true}));
  assert(ownedCore.length===1,'exactly one core belongs to the disposable Launcher');
  assert(path.resolve(ownedCore[0].ExecutablePath)===path.resolve(path.dirname(exe),'resources/runtime/core/PokeApp.Core.exe'),'owned packaged core path');
  execFileSync('taskkill.exe',['/PID',String(ownedCore[0].ProcessId),'/F'],{stdio:'ignore',windowsHide:true});
  let restarted;
  for(let n=0;n<80;n++) {
    restarted=await shell.evaluate(()=>window.launcher.core()).catch(()=>null);
    if(restarted?.status==='READY'&&restarted.starts===2) break;
    await pause(250);
  }
  assert(restarted?.status==='READY'&&restarted.starts===2,'packaged core recovers after an external idle-core failure');
  state=await shell.evaluate(()=>window.launcher.state());
  assert(state.local_status&&!state.principal&&!state.selected_save,'same isolated profile answers after recovery');
  report.checks.push('Core restarts automatically after an idle crash','Same isolated profile answers after recovery');
  report.status='PASS';
} catch(error) {
  report.status='FAIL';report.error=error.message;
} finally {
  if(browser) {
    const session=await browser.newBrowserCDPSession();
    await Promise.race([session.send('Browser.close').catch(()=>{}),pause(1000)]);
    await browser.close().catch(()=>{});
  }
  await pause(1200);
  if(child.exitCode===null) child.kill();
  await writeFile(path.join(output,'acceptance.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
}
process.exitCode=report.status==='PASS'?0:1;
