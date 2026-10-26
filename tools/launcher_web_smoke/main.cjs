// Real Electron check of the isolated web view policy with a local test origin.
const { app, BrowserWindow, WebContentsView } = require("electron");
const http = require("node:http");
const webview = require("../../companion/launcher/webview.cjs");

const page = `<!doctype html><title>t</title><body>
<a id="ok" href="/__launcher/quick-items/rare_candy">ok</a>
<a id="bad" href="/__launcher/quick-items/master_ball">bad</a>
<a id="ext" href="https://example.org/">ext</a>
<a id="evil" href="http://evil.test/">evil</a>
<script>window.probe = { launcher: typeof window.launcher, require: typeof require, process: typeof process, ua: navigator.userAgent };</script>`;
const server = http.createServer((req, res) =>
  res.writeHead(200, { "content-type": "text/html" }).end(page),
);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
app.whenReady().then(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const win = new BrowserWindow({ show: false, width: 900, height: 700 });
  const view = new WebContentsView({
    webPreferences: webview.webPreferences(),
  });
  win.contentView.addChildView(view);
  const quick = [],
    external = [],
    out = [];
  const check = (ok, label) => out.push([Boolean(ok), label]);
  await webview.attach(view, {
    origin,
    version: "0.23.0-test",
    onQuickItems: (i) => quick.push(i),
    openExternal: (u) => external.push(u),
  });
  const run = (js) => view.webContents.executeJavaScript(js);
  const probe = await run("window.probe");
  check(
    probe.launcher === "undefined" &&
      probe.require === "undefined" &&
      probe.process === "undefined",
    "no launcher bridge, require or process in the web",
  );
  check(
    /PokeAppLauncher\/0\.23\.0-test/.test(probe.ua),
    "launcher marker in user agent",
  );
  for (const id of ["ok", "bad", "ext", "evil"]) {
    await run(`document.getElementById('${id}').click()`);
    await sleep(300);
  }
  await run(
    "window.open('https://example.org/popup'); window.open('http://evil.test/popup')",
  );
  await sleep(300);
  check(
    JSON.stringify(quick) === JSON.stringify(["rare_candy"]),
    "only the approved quick-item bridge fires",
  );
  check(
    JSON.stringify(external) ===
      JSON.stringify(["https://example.org/", "https://example.org/popup"]),
    "HTTPS links/popups go to the external browser only",
  );
  check(
    new URL(view.webContents.getURL()).origin === origin &&
      new URL(view.webContents.getURL()).pathname === "/",
    "web view never left its origin or page",
  );
  check(BrowserWindow.getAllWindows().length === 1, "no popup window created");
  for (const [ok, label] of out) console.log((ok ? "PASS " : "FAIL ") + label);
  server.close();
  app.exit(out.every(([ok]) => ok) ? 0 : 1);
});
