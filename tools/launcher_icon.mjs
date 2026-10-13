// Lossless rasterization of the existing project SVG, no new visual design.
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { readFile, writeFile, mkdir } from "node:fs/promises";
const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 256, height: 256 } });
  const svg = await readFile("web/public/favicon.svg", "utf8");
  await page.setContent(
    `<style>html,body{margin:0;width:256px;height:256px}svg{display:block;width:256px;height:256px}</style>${svg}`,
  );
  const png = await page.screenshot({ omitBackground: true });
  const header = Buffer.alloc(22);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(1, 4);
  header.writeUInt16LE(1, 10);
  header.writeUInt16LE(32, 12);
  header.writeUInt32LE(png.length, 14);
  header.writeUInt32LE(22, 18);
  await mkdir("companion/launcher/assets", { recursive: true });
  await writeFile(
    "companion/launcher/assets/icon.ico",
    Buffer.concat([header, png]),
  );
} finally {
  await browser.close();
}
