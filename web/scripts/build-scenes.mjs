// Liga Nocturna art pass 2: original backdrop illustrations for PokeApp.
// Every shape is generated here from geometry and a seeded random sequence, so
// the art is reproducible, reviewable and owned by the project (no third-party
// images, no traced game assets). Run: node scripts/build-scenes.mjs
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const OUT = new URL("../src/design/scenes/", import.meta.url);
mkdirSync(OUT, { recursive: true });

// Palette primitives (mirror of src/design/tokens.css).
const C = {
  bg0: "#0a0d22",
  bg1: "#0f1430",
  s1: "#151b3d",
  s2: "#1c2350",
  s3: "#252e63",
  line: "#333f80",
  line2: "#4d5aa6",
  muted: "#9aa4d8",
  soft: "#ccd2f2",
  text: "#f5f7ff",
  teal: "#2de2c8",
  tealSoft: "#a9f6ea",
  tealDeep: "#0c3a45",
  gold: "#ffcc3d",
  goldSoft: "#ffe7a3",
  goldDeep: "#3d300c",
  info: "#5f9dff",
  infoSoft: "#bed6ff",
  violet: "#a68bff",
  violetSoft: "#ddd2ff",
  warm: "#ff9a4d",
  warmSoft: "#ffd2ad",
  warmDeep: "#44220f",
  danger: "#ff5c8a",
  magenta: "#ff3d8b",
  leaf: "#9be15d",
};
const n = (v) => Math.round(v * 10) / 10;
function rng(seed) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const svg = (w, h, body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${body}</svg>\n`;
const save = (name, content) => {
  writeFileSync(new URL(name, OUT), content);
  console.log(name.padEnd(22), String(content.length).padStart(6), "bytes");
};
const star4 = (x, y, r) =>
  `M${n(x)} ${n(y - r)}Q${n(x + r * 0.18)} ${n(y - r * 0.18)} ${n(x + r)} ${n(y)}Q${n(x + r * 0.18)} ${n(y + r * 0.18)} ${n(x)} ${n(y + r)}Q${n(x - r * 0.18)} ${n(y + r * 0.18)} ${n(x - r)} ${n(y)}Q${n(x - r * 0.18)} ${n(y - r * 0.18)} ${n(x)} ${n(y - r)}Z`;
// A ball emblem: ring, equator band and centre button (outline only).
const ball = (x, y, r, stroke, width, extra = "") =>
  `<g fill="none" stroke="${stroke}" stroke-width="${width}" ${extra}><circle cx="${n(x)}" cy="${n(y)}" r="${n(r)}"/><path d="M${n(x - r)} ${n(y)}H${n(x - r * 0.3)}M${n(x + r * 0.3)} ${n(y)}H${n(x + r)}"/><circle cx="${n(x)}" cy="${n(y)}" r="${n(r * 0.3)}"/><circle cx="${n(x)}" cy="${n(y)}" r="${n(r * 0.14)}"/></g>`;

/* ---------- Night sky tile (all screens) ---------- */
{
  const r = rng(7),
    W = 480,
    H = 480;
  const groups = {
    [C.text]: [],
    [C.tealSoft]: [],
    [C.goldSoft]: [],
    [C.violetSoft]: [],
  };
  const keys = Object.keys(groups);
  for (let i = 0; i < 70; i++) {
    const color = r() < 0.7 ? C.text : keys[1 + Math.floor(r() * 3)];
    groups[color].push(
      `<circle cx="${n(r() * W)}" cy="${n(r() * H)}" r="${n(0.4 + r() * r() * 1.4)}" opacity="${n(0.25 + r() * 0.65)}"/>`,
    );
  }
  let body = Object.entries(groups)
    .map(([c, d]) => `<g fill="${c}">${d.join("")}</g>`)
    .join("");
  body += `<g fill="${C.text}" opacity=".7">${[0, 1, 2, 3].map(() => `<path d="${star4(20 + r() * (W - 40), 20 + r() * (H - 40), 3 + r() * 3)}"/>`).join("")}</g>`;
  save("starfield.svg", svg(W, H, body));
}

/* ---------- Rising sparkles tile (show screens) ---------- */
{
  const r = rng(11),
    W = 600,
    H = 900;
  const palette = [C.goldSoft, C.tealSoft, C.text, C.warmSoft];
  let body = "";
  for (let i = 0; i < 22; i++) {
    const x = r() * W,
      y = r() * H,
      c = palette[Math.floor(r() * palette.length)],
      o = n(0.35 + r() * 0.55);
    body +=
      r() < 0.35
        ? `<path d="${star4(x, y, 3 + r() * 4)}" fill="${c}" opacity="${o}"/>`
        : `<circle cx="${n(x)}" cy="${n(y)}" r="${n(1 + r() * 2)}" fill="${c}" opacity="${o}"/>`;
  }
  save("sparkles.svg", svg(W, H, body));
}

/* ---------- INICIO: the night stadium ---------- */
{
  const r = rng(21),
    W = 1600,
    H = 900,
    cx = 800,
    py = 760;
  let body = `<defs>
<linearGradient id="st" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.s3}"/><stop offset="1" stop-color="${C.bg1}"/></linearGradient>
<radialGradient id="pi" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="${C.tealDeep}"/><stop offset=".8" stop-color="#0b2433"/><stop offset="1" stop-color="${C.bg0}"/></radialGradient>
<linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.text}" stop-opacity=".3"/><stop offset="1" stop-color="${C.text}" stop-opacity="0"/></linearGradient>
<radialGradient id="lamp"><stop offset="0" stop-color="${C.text}" stop-opacity=".9"/><stop offset=".25" stop-color="${C.tealSoft}" stop-opacity=".45"/><stop offset="1" stop-color="${C.teal}" stop-opacity="0"/></radialGradient>
<radialGradient id="halo" cx=".5" cy="1" r=".7"><stop offset="0" stop-color="${C.teal}" stop-opacity=".35"/><stop offset="1" stop-color="${C.teal}" stop-opacity="0"/></radialGradient>
<clipPath id="pc"><ellipse cx="${cx}" cy="${py}" rx="640" ry="150"/></clipPath>
</defs>`;
  // Roof canopy and stands
  body += `<path d="M-60 ${py}C120 250 520 150 ${cx} 150S1480 250 1660 ${py}Z" fill="url(#st)" opacity=".95"/>`;
  body += `<path d="M-60 ${py}C120 250 520 150 ${cx} 150S1480 250 1660 ${py}" fill="none" stroke="${C.teal}" stroke-width="3" opacity=".55"/>`;
  body += `<path d="M-20 ${py}C150 300 530 205 ${cx} 205S1450 300 1620 ${py}" fill="none" stroke="${C.line2}" stroke-width="1.5" opacity=".6"/>`;
  const tiers = 9;
  for (let t = 0; t < tiers; t++) {
    const k = t / tiers;
    const top = 215 + k * 360,
      side = 20 + k * 120;
    body += `<path d="M${side} ${py}C${150 + k * 160} ${300 + k * 280} ${530 + k * 60} ${top} ${cx} ${top}S${1450 - k * 160} ${300 + k * 280} ${W - side} ${py}" fill="none" stroke="${C.line}" stroke-width="1" opacity="${n(0.55 - k * 0.3)}"/>`;
  }
  // Crowd: coloured dots on the stands, denser near the top tiers
  const crowd = {
    [C.teal]: [],
    [C.magenta]: [],
    [C.gold]: [],
    [C.info]: [],
    [C.text]: [],
  };
  const ckeys = Object.keys(crowd);
  for (let i = 0; i < 520; i++) {
    const a = r() * Math.PI,
      k = Math.pow(r(), 0.8);
    const rx = 760 - k * 120,
      ry = 560 - k * 420;
    const x = cx - Math.cos(a) * rx * (0.98 + r() * 0.04),
      y = py - Math.sin(a) * ry - 30;
    if (y > py - 170 && Math.abs(x - cx) < 640) continue;
    crowd[ckeys[Math.floor(r() * ckeys.length)]].push(
      `<circle cx="${n(x)}" cy="${n(y)}" r="${n(1.3 + r() * 1.3)}"/>`,
    );
  }
  body += Object.entries(crowd)
    .map(([c, d]) => `<g fill="${c}" opacity=".5">${d.join("")}</g>`)
    .join("");
  // Pitch with mowing stripes, lines and the ball emblem in the centre circle
  body += `<ellipse cx="${cx}" cy="${py}" rx="650" ry="158" fill="url(#pi)"/>`;
  body += `<g clip-path="url(#pc)" fill="${C.teal}" opacity=".07">${Array.from({ length: 16 }, (_, i) => (i % 2 ? `<rect x="${160 + i * 80}" y="${py - 160}" width="80" height="320"/>` : "")).join("")}</g>`;
  body += `<g fill="none" stroke="${C.tealSoft}" stroke-width="2" opacity=".45"><ellipse cx="${cx}" cy="${py}" rx="600" ry="132"/><path d="M${cx} ${py - 132}V${py + 132}"/><ellipse cx="${cx}" cy="${py}" rx="120" ry="32"/></g>`;
  body += `<g transform="translate(${cx} ${py}) scale(1 .27)">${ball(0, 0, 92, C.tealSoft, 5, 'opacity=".75"')}</g>`;
  body += `<ellipse cx="${cx}" cy="${py - 40}" rx="700" ry="240" fill="url(#halo)"/>`;
  // Floodlight masts, heads and light cones
  for (const x of [250, 1350]) {
    const dir = x < cx ? 1 : -1;
    body += `<path d="M${x - 70} 110L${x + 70} 110L${cx + dir * -40} ${py + 40}L${cx - dir * 520} ${py + 40}Z" fill="url(#cone)" opacity=".55"/>`;
    body += `<path d="M${x} 150V${py - 40}" stroke="${C.line2}" stroke-width="7"/><path d="M${x - 14} ${py - 40}H${x + 14}" stroke="${C.line2}" stroke-width="5"/>`;
    body += `<circle cx="${x}" cy="110" r="120" fill="url(#lamp)"/><rect x="${x - 58}" y="86" width="116" height="48" rx="8" fill="${C.s3}" stroke="${C.tealSoft}" stroke-width="1.5"/>`;
    body += `<g fill="${C.text}">${Array.from({ length: 12 }, (_, i) => `<circle cx="${x - 45 + (i % 6) * 18}" cy="${100 + Math.floor(i / 6) * 20}" r="5.5"/>`).join("")}</g>`;
  }
  // Jumbotron over the stands
  body += `<g transform="translate(${cx - 150} 52)"><rect width="300" height="86" rx="10" fill="${C.bg1}" stroke="${C.teal}" stroke-width="2" opacity=".95"/><rect x="14" y="14" width="120" height="58" rx="6" fill="${C.tealDeep}"/><rect x="166" y="14" width="120" height="58" rx="6" fill="#3a1030"/>${ball(74, 43, 18, C.teal, 3)}${ball(226, 43, 18, C.magenta, 3)}<path d="M146 30L154 43L146 56" fill="none" stroke="${C.goldSoft}" stroke-width="3"/><path d="M${150 - 40} 86V112M${150 + 40} 86V112" stroke="${C.line2}" stroke-width="4"/></g>`;
  // Camera-flash glints scattered in the stands (CSS twinkles a copy of these)
  body += `<g fill="${C.text}">${Array.from({ length: 12 }, () => `<path d="${star4(140 + r() * 1320, 230 + r() * 300, 4 + r() * 4)}" opacity="${n(0.4 + r() * 0.5)}"/>`).join("")}</g>`;
  save("stadium.svg", svg(W, H, body));
}

/* ---------- TIENDA: a warm Pokémon market ---------- */
{
  const r = rng(31),
    W = 1600,
    H = 1000;
  let body = `<defs>
<radialGradient id="lg"><stop offset="0" stop-color="${C.goldSoft}" stop-opacity=".55"/><stop offset=".4" stop-color="${C.warm}" stop-opacity=".18"/><stop offset="1" stop-color="${C.warm}" stop-opacity="0"/></radialGradient>
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.warmDeep}" stop-opacity=".55"/><stop offset="1" stop-color="${C.bg0}" stop-opacity="0"/></linearGradient>
</defs>`;
  body += `<rect x="720" y="0" width="880" height="${H}" fill="url(#wall)"/>`;
  body += `<g stroke="${C.warm}" stroke-width="1" opacity=".08">${Array.from({ length: 22 }, (_, i) => `<path d="M${740 + i * 40} 0V${H}"/>`).join("")}</g>`;
  // Pennant garland across the top
  let flags = `<path d="M700 70Q1150 150 1600 60" fill="none" stroke="${C.warmSoft}" stroke-width="2" opacity=".5"/>`;
  for (let i = 0; i < 17; i++) {
    const t = i / 16,
      x = 700 + t * 900,
      y = 70 + Math.sin(t * Math.PI) * 52 - t * 10;
    const c = [C.warm, C.goldSoft, C.danger, C.tealSoft][i % 4];
    flags += `<path d="M${n(x - 16)} ${n(y)}L${n(x + 16)} ${n(y)}L${n(x)} ${n(y + 34)}Z" fill="${c}" opacity=".55"/>`;
  }
  body += flags;
  // Hanging lamps with warm glows
  for (const x of [900, 1200, 1480]) {
    body += `<path d="M${x} 0V150" stroke="${C.warmSoft}" stroke-width="2" opacity=".5"/><circle cx="${x}" cy="200" r="170" fill="url(#lg)"/><path d="M${x - 36} 186L${x - 18} 150H${x + 18}L${x + 36} 186Z" fill="${C.warm}" opacity=".85"/><ellipse cx="${x}" cy="188" rx="22" ry="7" fill="${C.goldSoft}"/>`;
  }
  // Shelving with items: balls, sprays, berries, gift boxes
  const item = (x, y) => {
    const k = r();
    if (k < 0.35) {
      const top = [C.danger, C.info, C.gold, C.violet][Math.floor(r() * 4)];
      return `<path d="M${n(x - 15)} ${n(y - 15)}A15 15 0 0 1 ${n(x + 15)} ${n(y - 15)}Z" fill="${top}" transform="translate(0 0)"/><path d="M${n(x - 15)} ${n(y - 15)}A15 15 0 0 0 ${n(x + 15)} ${n(y - 15)}Z" fill="${C.soft}"/><path d="M${n(x - 15)} ${n(y - 15)}H${n(x + 15)}" stroke="${C.bg0}" stroke-width="2.5"/><circle cx="${n(x)}" cy="${n(y - 15)}" r="4.5" fill="${C.text}" stroke="${C.bg0}" stroke-width="2"/>`;
    }
    if (k < 0.6) {
      const c = [C.violet, C.info, C.teal][Math.floor(r() * 3)];
      return `<rect x="${n(x - 10)}" y="${n(y - 38)}" width="20" height="38" rx="6" fill="${c}"/><rect x="${n(x - 5)}" y="${n(y - 46)}" width="10" height="9" rx="2" fill="${C.soft}"/><rect x="${n(x - 10)}" y="${n(y - 26)}" width="20" height="9" fill="${C.text}" opacity=".7"/>`;
    }
    if (k < 0.82) {
      const c = [C.magenta, C.warm, C.violet][Math.floor(r() * 3)];
      return `<circle cx="${n(x)}" cy="${n(y - 13)}" r="13" fill="${c}"/><path d="M${n(x)} ${n(y - 26)}q8 -10 16 -6q-6 8 -16 6z" fill="${C.leaf}"/><circle cx="${n(x - 4)}" cy="${n(y - 17)}" r="3" fill="${C.text}" opacity=".45"/>`;
    }
    return `<rect x="${n(x - 18)}" y="${n(y - 30)}" width="36" height="30" rx="3" fill="${C.warm}" opacity=".9"/><path d="M${n(x)} ${n(y - 30)}V${n(y)}M${n(x - 18)} ${n(y - 18)}H${n(x + 18)}" stroke="${C.goldSoft}" stroke-width="4"/>`;
  };
  for (const [sx, sw] of [
    [820, 300],
    [1170, 380],
  ]) {
    body += `<rect x="${sx - 14}" y="300" width="${sw + 28}" height="660" rx="10" fill="${C.s1}" stroke="${C.warm}" stroke-width="1.5" opacity=".75"/>`;
    for (let s = 0; s < 5; s++) {
      const y = 420 + s * 128;
      let x = sx + 20;
      while (x < sx + sw - 20) {
        body += item(x, y);
        x += 46 + r() * 18;
      }
      body += `<rect x="${sx - 6}" y="${y}" width="${sw + 12}" height="12" rx="3" fill="${C.warmDeep}"/><rect x="${sx - 6}" y="${y}" width="${sw + 12}" height="3" fill="${C.warm}" opacity=".7"/>`;
      if (s % 2 === 0)
        body += `<rect x="${n(sx + sw * (0.3 + r() * 0.4))}" y="${y + 14}" width="34" height="16" rx="3" fill="${C.goldSoft}" opacity=".8"/>`;
    }
  }
  save("market.svg", svg(W, H, body));
}

/* ---------- SCOUTING: a tactical scope over a hex field ---------- */
{
  const W = 1600,
    H = 1000,
    cx = 1150,
    cy = 430;
  let body = `<defs><pattern id="hx" width="56" height="97" patternUnits="userSpaceOnUse"><path d="M28 0L56 16V48L28 64L0 48V16ZM28 64V97" fill="none" stroke="${C.info}" stroke-width="1"/></pattern>
<radialGradient id="fade" cx="${cx / W}" cy="${cy / H}" r=".55"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<mask id="m"><rect width="${W}" height="${H}" fill="url(#fade)"/></mask>
<radialGradient id="core"><stop offset="0" stop-color="${C.info}" stop-opacity=".22"/><stop offset="1" stop-color="${C.info}" stop-opacity="0"/></radialGradient></defs>`;
  body += `<rect width="${W}" height="${H}" fill="url(#hx)" opacity=".22" mask="url(#m)"/>`;
  body += `<circle cx="${cx}" cy="${cy}" r="470" fill="url(#core)"/>`;
  body += `<g fill="none" stroke="${C.infoSoft}">`;
  [110, 200, 290, 380, 460].forEach((rad, i) => {
    body += `<circle cx="${cx}" cy="${cy}" r="${rad}" stroke-width="${i === 3 ? 2 : 1}" opacity="${n(0.5 - i * 0.06)}" ${i === 2 ? 'stroke-dasharray="6 10"' : ""}/>`;
  });
  body += `</g>`;
  let ticks = "";
  for (let d = 0; d < 360; d += 5) {
    const a = (d * Math.PI) / 180,
      len = d % 30 === 0 ? 22 : d % 15 === 0 ? 14 : 7;
    ticks += `M${n(cx + Math.cos(a) * 380)} ${n(cy + Math.sin(a) * 380)}L${n(cx + Math.cos(a) * (380 + len))} ${n(cy + Math.sin(a) * (380 + len))}`;
  }
  body += `<path d="${ticks}" stroke="${C.infoSoft}" stroke-width="1.5" opacity=".55"/>`;
  body += `<path d="M${cx - 500} ${cy}H${cx - 120}M${cx + 120} ${cy}H${cx + 500}M${cx} ${cy - 500}V${cy - 120}M${cx} ${cy + 120}V${cy + 500}" stroke="${C.info}" stroke-width="1.5" opacity=".45"/>`;
  // Lock-on brackets around the centre
  const b = 70,
    l = 22;
  body += `<path d="M${cx - b} ${cy - b + l}V${cy - b}H${cx - b + l}M${cx + b - l} ${cy - b}H${cx + b}V${cy - b + l}M${cx + b} ${cy + b - l}V${cy + b}H${cx + b - l}M${cx - b + l} ${cy + b}H${cx - b}V${cy + b - l}" fill="none" stroke="${C.teal}" stroke-width="3" opacity=".8"/>`;
  body += ball(cx, cy, 34, C.tealSoft, 2.5, 'opacity=".7"');
  // Data callouts: leader lines with readout bars
  for (const [ax, ay, dx, dy] of [
    [cx + 200, cy - 260, 180, -60],
    [cx - 300, cy - 220, -220, -80],
    [cx + 260, cy + 220, 170, 70],
    [cx - 260, cy + 260, -200, 60],
  ]) {
    const ex = ax + dx,
      ey = ay + dy,
      sgn = Math.sign(dx);
    body += `<path d="M${ax} ${ay}L${ex} ${ey}H${ex + sgn * 120}" fill="none" stroke="${C.infoSoft}" stroke-width="1.2" opacity=".5"/><circle cx="${ax}" cy="${ay}" r="5" fill="${C.teal}" opacity=".85"/>`;
    const bx = sgn > 0 ? ex + 10 : ex - 110;
    body += `<g fill="${C.infoSoft}" opacity=".35"><rect x="${bx}" y="${ey + 10}" width="100" height="6" rx="3"/><rect x="${bx}" y="${ey + 22}" width="64" height="6" rx="3"/><rect x="${bx}" y="${ey + 34}" width="82" height="6" rx="3"/></g>`;
  }
  // Corner frame of the dossier
  body += `<path d="M760 60H740V80M1560 60H1580V80M1580 940V960H1560M740 940V960H760" fill="none" stroke="${C.info}" stroke-width="2" opacity=".5"/>`;
  save("scope.svg", svg(W, H, body));
}

/* ---------- LIGA: banners, trophy and golden rays ---------- */
{
  const W = 1600,
    H = 1000,
    tx = 1180;
  let body = `<defs><radialGradient id="ray" cx="${tx / W}" cy=".42" r=".6"><stop offset="0" stop-color="${C.gold}" stop-opacity=".5"/><stop offset="1" stop-color="${C.gold}" stop-opacity="0"/></radialGradient>
<linearGradient id="tro" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${C.goldSoft}"/><stop offset=".5" stop-color="${C.gold}"/><stop offset="1" stop-color="#b8861c"/></linearGradient>
<linearGradient id="ban" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.s3}"/><stop offset="1" stop-color="${C.s1}"/></linearGradient></defs>`;
  let rays = "";
  for (let i = 0; i < 18; i++) {
    const a = (i / 18) * Math.PI * 2,
      w = 0.07;
    rays += `M${tx} 420L${n(tx + Math.cos(a - w) * 900)} ${n(420 + Math.sin(a - w) * 900)}L${n(tx + Math.cos(a + w) * 900)} ${n(420 + Math.sin(a + w) * 900)}Z`;
  }
  body += `<path d="${rays}" fill="url(#ray)" opacity=".35"/>`;
  // Hanging banners
  for (let i = 0; i < 6; i++) {
    const x = 760 + i * 140,
      h = 300 + (i % 2) * 60,
      gold = i % 2 === 0;
    body += `<path d="M${x} 0H${x + 92}V${h}L${x + 46} ${h - 34}L${x} ${h}Z" fill="url(#ban)" stroke="${gold ? C.gold : C.line2}" stroke-width="2" opacity=".85"/>`;
    body += `<path d="M${x + 10} 20V${h - 40}M${x + 82} 20V${h - 40}" stroke="${gold ? C.goldSoft : C.line2}" stroke-width="1.5" opacity=".5"/>`;
    body += gold
      ? ball(x + 46, 110, 26, C.goldSoft, 3)
      : `<path d="${star4(x + 46, 110, 22)}" fill="${C.goldSoft}" opacity=".7"/>`;
  }
  // Trophy
  body += `<g transform="translate(${tx} 420)"><path d="M-110 -150H110C110 -40 70 30 0 40C-70 30 -110 -40 -110 -150Z" fill="url(#tro)"/><path d="M-110 -120C-180 -120 -190 -30 -100 -10M110 -120C180 -120 190 -30 100 -10" fill="none" stroke="${C.gold}" stroke-width="14"/><rect x="-18" y="38" width="36" height="70" fill="${C.gold}"/><path d="M-80 108H80L96 160H-96Z" fill="#b8861c"/><rect x="-110" y="160" width="220" height="30" rx="6" fill="${C.goldDeep}" stroke="${C.gold}" stroke-width="2"/>${ball(0, -70, 42, C.goldDeep, 6)}<path d="M-70 -138C-60 -60 -20 -10 10 10" stroke="${C.text}" stroke-width="8" opacity=".35" fill="none"/></g>`;
  // Laurel branches rising around the cup (same construction as the Hall)
  let laurel = "";
  for (const side of [-1, 1]) {
    for (let i = 0; i < 11; i++) {
      const t = 0.3 + (i / 10) * 0.55,
        a = Math.PI / 2 + side * t * Math.PI;
      const x = tx + Math.cos(a) * 235,
        y = 360 + Math.sin(a) * 235;
      laurel += `<ellipse cx="${n(x)}" cy="${n(y)}" rx="28" ry="10" transform="rotate(${n((a * 180) / Math.PI + side * 60)} ${n(x)} ${n(y)})"/>`;
    }
  }
  body += `<g fill="${C.gold}" opacity=".45">${laurel}</g>`;
  // Podium
  body += `<g fill="${C.s2}" stroke="${C.gold}" stroke-width="2" opacity=".85"><rect x="${tx - 90}" y="700" width="180" height="120"/><rect x="${tx - 270}" y="750" width="180" height="70"/><rect x="${tx + 90}" y="770" width="180" height="50"/></g>`;
  save("league.svg", svg(W, H, body));
}

/* ---------- PERFIL: a trainer licence guilloché ---------- */
{
  const W = 1600,
    H = 1000;
  const rosette = (cx, cy, R, a, k, turns, stroke, opacity, width) => {
    let paths = "";
    for (let j = 0; j < turns; j++) {
      const off = (j / turns) * Math.PI * 2;
      let d = "";
      // 2° steps and whole pixels: invisible at this stroke width, half the bytes.
      for (let s = 0; s < 360; s += 2) {
        const t = (s / 360) * Math.PI * 2;
        const rad = R + a * Math.sin(k * t + off);
        d += `${s ? "L" : "M"}${Math.round(cx + Math.cos(t) * rad)} ${Math.round(cy + Math.sin(t) * rad)}`;
      }
      paths += `<path d="${d}Z"/>`;
    }
    return `<g fill="none" stroke="${stroke}" stroke-width="${width}" opacity="${opacity}">${paths}</g>`;
  };
  let body = rosette(1180, 380, 300, 40, 18, 6, C.infoSoft, ".35", 1);
  body += rosette(1180, 380, 190, 22, 12, 5, C.teal, ".35", 1);
  body += rosette(1180, 380, 420, 26, 24, 3, C.info, ".25", 1);
  body += ball(1180, 380, 110, C.infoSoft, 4, 'opacity=".4"');
  let micro = "";
  for (let i = 0; i < 26; i++)
    micro += `M760 ${640 + i * 12}Q1180 ${600 + i * 12 + (i % 2) * 18} 1600 ${640 + i * 12}`;
  body += `<path d="${micro}" fill="none" stroke="${C.info}" stroke-width=".8" opacity=".25"/>`;
  // Badge case outlines
  for (let i = 0; i < 8; i++) {
    const x = 860 + i * 86,
      y = 900;
    body += `<path d="M${x} ${y - 30}L${x + 26} ${y - 15}V${y + 15}L${x} ${y + 30}L${x - 26} ${y + 15}V${y - 15}Z" fill="none" stroke="${C.goldSoft}" stroke-width="1.5" opacity=".4"/>`;
  }
  save("licence.svg", svg(W, H, body));
}

/* ---------- HALL: laurel wreath and spotlight ---------- */
{
  const W = 1600,
    H = 1000,
    cx = 1150,
    cy = 360;
  let body = `<defs><linearGradient id="sp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.goldSoft}" stop-opacity=".4"/><stop offset="1" stop-color="${C.gold}" stop-opacity="0"/></linearGradient></defs>`;
  body += `<path d="M${cx - 60} 0H${cx + 60}L${cx + 340} 900H${cx - 340}Z" fill="url(#sp)"/>`;
  let leaves = "";
  for (const side of [-1, 1]) {
    for (let i = 0; i < 14; i++) {
      const t = 0.25 + (i / 13) * 0.62,
        a = Math.PI / 2 + side * t * Math.PI;
      const x = cx + Math.cos(a) * 250,
        y = cy + Math.sin(a) * 250;
      leaves += `<ellipse cx="${n(x)}" cy="${n(y)}" rx="34" ry="12" transform="rotate(${n((a * 180) / Math.PI + side * 60)} ${n(x)} ${n(y)})"/>`;
    }
  }
  body += `<g fill="${C.gold}" opacity=".5">${leaves}</g>`;
  body += `<path d="M${cx - 248} ${cy + 20}A250 250 0 0 0 ${cx - 20} ${cy + 250}M${cx + 248} ${cy + 20}A250 250 0 0 1 ${cx + 20} ${cy + 250}" fill="none" stroke="${C.goldSoft}" stroke-width="3" opacity=".5"/>`;
  const r = rng(51);
  body += `<g fill="${C.goldSoft}">${Array.from({ length: 16 }, () => `<path d="${star4(760 + r() * 820, 40 + r() * 760, 3 + r() * 7)}" opacity="${n(0.3 + r() * 0.6)}"/>`).join("")}</g>`;
  save("hall.svg", svg(W, H, body));
}

/* ---------- MI PC: a dual-screen handheld showing a box ---------- */
{
  const W = 1600,
    H = 1000,
    x0 = 840,
    w = 620;
  const r = rng(61);
  let body = `<defs><linearGradient id="shell" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.s3}"/><stop offset="1" stop-color="${C.s1}"/></linearGradient>
<linearGradient id="scr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#12304a"/><stop offset="1" stop-color="${C.bg1}"/></linearGradient>
<pattern id="wp" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M0 24L24 0" stroke="${C.leaf}" stroke-width="2" opacity=".18"/></pattern></defs>`;
  // Upper half: the box screen, with a wallpaper, a title tab and 30 slots
  body += `<rect x="${x0}" y="70" width="${w}" height="420" rx="34" fill="url(#shell)" stroke="${C.line2}" stroke-width="2"/>`;
  body += `<rect x="${x0 + 40}" y="110" width="${w - 80}" height="340" rx="12" fill="url(#scr)" stroke="${C.leaf}" stroke-width="2" opacity=".95"/>`;
  body += `<rect x="${x0 + 40}" y="110" width="${w - 80}" height="340" rx="12" fill="url(#wp)"/>`;
  body += `<rect x="${x0 + w / 2 - 90}" y="124" width="180" height="34" rx="17" fill="${C.leaf}" opacity=".85"/><path d="M${x0 + w / 2 - 120} 141l-12 0m0 0l8-8m-8 8l8 8M${x0 + w / 2 + 120} 141l12 0m0 0l-8-8m8 8l-8 8" stroke="${C.leaf}" stroke-width="3" fill="none" opacity=".7"/>`;
  for (let row = 0; row < 5; row++)
    for (let col = 0; col < 6; col++) {
      const x = x0 + 66 + col * 82,
        y = 176 + row * 52;
      body += `<rect x="${x}" y="${y}" width="68" height="42" rx="8" fill="none" stroke="${C.tealSoft}" stroke-width="1.2" opacity=".35"/>`;
      if (r() < 0.42)
        body += ball(
          x + 34,
          y + 21,
          13,
          C.tealSoft,
          2,
          `opacity="${n(0.45 + r() * 0.4)}"`,
        );
    }
  // Hinge
  body += `<rect x="${x0 + 30}" y="490" width="${w - 60}" height="34" rx="12" fill="${C.s2}" stroke="${C.line2}" stroke-width="1.5"/><circle cx="${x0 + 70}" cy="507" r="5" fill="${C.leaf}"/>`;
  // Lower half: touch screen with the party, d-pad and buttons
  body += `<rect x="${x0}" y="524" width="${w}" height="400" rx="34" fill="url(#shell)" stroke="${C.line2}" stroke-width="2"/>`;
  body += `<rect x="${x0 + 150}" y="560" width="${w - 300}" height="250" rx="10" fill="url(#scr)" stroke="${C.leaf}" stroke-width="2" opacity=".9"/>`;
  for (let i = 0; i < 6; i++) {
    const x = x0 + 178 + (i % 3) * 92,
      y = 584 + Math.floor(i / 3) * 108;
    body += `<rect x="${x}" y="${y}" width="80" height="92" rx="10" fill="${C.leaf}" opacity=".1" stroke="${C.leaf}" stroke-width="1.2"/>`;
    body += ball(x + 40, y + 40, 18, C.leaf, 2.2, 'opacity=".7"');
    body += `<rect x="${x + 16}" y="${y + 70}" width="48" height="6" rx="3" fill="${C.leaf}" opacity=".45"/>`;
  }
  const dx = x0 + 72,
    dy = 640;
  body += `<path d="M${dx - 14} ${dy - 42}h28v28h28v28h-28v28h-28v-28h-28v-28h28z" fill="${C.bg1}" stroke="${C.line2}" stroke-width="2"/>`;
  const bx = x0 + w - 72;
  [
    [0, -30, C.leaf],
    [30, 0, C.teal],
    [0, 30, C.info],
    [-30, 0, C.gold],
  ].forEach(([ox, oy, c]) => {
    body += `<circle cx="${bx + ox}" cy="${dy + oy}" r="15" fill="${C.bg1}" stroke="${c}" stroke-width="2.5" opacity=".85"/>`;
  });
  body += `<rect x="${x0 + w / 2 - 50}" y="842" width="40" height="12" rx="6" fill="${C.line2}"/><rect x="${x0 + w / 2 + 10}" y="842" width="40" height="12" rx="6" fill="${C.line2}"/>`;
  save("terminal.svg", svg(W, H, body));
}

/* ---------- BATALLAS: a calm versus split ---------- */
{
  const W = 1600,
    H = 1000;
  let body = `<path d="M700 0H1150L950 1000H500Z" fill="${C.magenta}" opacity=".08"/><path d="M1150 0H1600V1000H950Z" fill="${C.info}" opacity=".08"/><path d="M1150 0L950 1000" stroke="${C.text}" stroke-width="3" opacity=".25"/>`;
  body += `<g fill="none" stroke="${C.line2}" stroke-width="1" opacity=".35">${Array.from({ length: 9 }, (_, i) => `<path d="M700 ${100 + i * 100}H1600"/>`).join("")}</g>`;
  body += `<g fill="${C.text}" opacity=".18"><path d="M1040 440l40 60l-40 60h30l40-60l-40-60z"/><path d="M1000 440l40 60l-40 60h30l40-60l-40-60z"/></g>`;
  save("versus.svg", svg(W, H, body));
}

/* ---------- COPA: a bracket climbing to a crown ---------- */
{
  const W = 1600,
    H = 1000;
  let d = "";
  const ys = Array.from({ length: 8 }, (_, i) => 150 + i * 95);
  let level = ys,
    x = 820;
  while (level.length > 1) {
    const next = [];
    for (let i = 0; i < level.length; i += 2) {
      const a = level[i],
        b = level[i + 1],
        m = (a + b) / 2;
      d += `M${x} ${a}H${x + 90}V${b}H${x}M${x + 90} ${m}H${x + 170}`;
      next.push(m);
    }
    level = next;
    x += 170;
  }
  let body = `<path d="${d}" fill="none" stroke="${C.violet}" stroke-width="2" opacity=".45"/>`;
  body += `<g fill="${C.violet}" opacity=".5">${ys.map((y) => `<circle cx="820" cy="${y}" r="6"/>`).join("")}</g>`;
  const fx = x,
    fy = level[0];
  body += `<path d="M${fx + 10} ${fy + 26}L${fx} ${fy - 20}L${fx + 30} ${fy}L${fx + 50} ${fy - 34}L${fx + 70} ${fy}L${fx + 100} ${fy - 20}L${fx + 90} ${fy + 26}Z" fill="${C.violetSoft}" opacity=".6"/>`;
  save("bracket.svg", svg(W, H, body));
}

/* ---------- Calm areas (Juicios, Saves, Admin): a blueprint ---------- */
{
  const W = 1600,
    H = 1000;
  let body = `<defs><pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="${C.line2}" stroke-width=".8"/></pattern></defs>`;
  body += `<rect x="760" y="0" width="840" height="${H}" fill="url(#g)" opacity=".3"/>`;
  body += ball(1220, 380, 220, C.line2, 2, 'opacity=".45"');
  body += `<path d="M760 760H1600" stroke="${C.line2}" stroke-width="1" opacity=".4"/>`;
  save("blueprint.svg", svg(W, H, body));
}

/* ---------- Launcher: the same night sky behind its native panels ----------
   Written into a marked block of companion/launcher/style.css as a data URI
   (its CSP allows img-src data:), so the package gains no new file. */
{
  const sky = readFileSync(new URL("starfield.svg", OUT), "utf8");
  const uri = `data:image/svg+xml,${encodeURIComponent(sky.trim()).replace(/'/g, "%27")}`;
  const block = `/* scenes:start — generated by web/scripts/build-scenes.mjs; do not edit */
body {
  background:
    url("${uri}") 0 0 / 480px 480px repeat,
    radial-gradient(60vw 50vw at 100% 0%, color-mix(in srgb, var(--c-magenta) 13%, transparent), transparent 70%),
    radial-gradient(55vw 45vw at 0% 100%, color-mix(in srgb, var(--c-accent) 12%, transparent), transparent 70%),
    linear-gradient(180deg, #070a1c 0%, var(--c-bg-0) 45%, #0c1030 100%) fixed;
  background-attachment: fixed;
}
/* scenes:end */`;
  const target = new URL("../../companion/launcher/style.css", import.meta.url);
  const css = readFileSync(target, "utf8");
  const next = /\/\* scenes:start[\s\S]*?scenes:end \*\//.test(css)
    ? css.replace(/\/\* scenes:start[\s\S]*?scenes:end \*\//, block)
    : `${css.trimEnd()}\n\n${block}\n`;
  writeFileSync(target, next);
  console.log("launcher style.css".padEnd(22), "night sky block updated");
}
