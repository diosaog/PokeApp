import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, overview, players } from "./fixtures";

// Spectator mode must show both full teams (6 vs 6) at once on a desktop
// screen: sprite, nickname, species, level, item and four moves with PP for
// every Pokémon, with no page or per-team scroll. On a big screen it grows
// with it, and a move's details open inside their own card without covering
// anything (owner, 2026-11-18). Synthetic data only.
type Mon = {
  species: string;
  nickname: string | null;
  level: number;
  types: string[];
  item: string | null;
  moves: { name: string; pp: number }[];
};
const mon = (
  species: string,
  nickname: string | null,
  level: number,
  types: string[],
  item: string | null,
  moves: [string, number][],
): Mon => ({
  species,
  nickname,
  level,
  types,
  item,
  moves: moves.map(([name, pp]) => ({ name, pp })),
});
const teamA = [
  mon("Garchomp", "Tiburón", 78, ["Dragon", "Ground"], "Choice Scarf", [
    ["Earthquake", 16],
    ["Outrage", 16],
    ["Stone Edge", 8],
    ["Fire Fang", 24],
  ]),
  mon("Gyarados", "Leviatán", 77, ["Water", "Flying"], "Leftovers", [
    ["Waterfall", 24],
    ["Dragon Dance", 32],
    ["Ice Fang", 24],
    ["Bounce", 8],
  ]),
  mon("Gardevoir", "Hada", 76, ["Psychic", "Fairy"], "Life Orb", [
    ["Moonblast", 24],
    ["Psychic", 16],
    ["Shadow Ball", 24],
    ["Calm Mind", 32],
  ]),
  mon("Ferrothorn", "Pinchos", 75, ["Grass", "Steel"], "Rocky Helmet", [
    ["Leech Seed", 16],
    ["Gyro Ball", 8],
    ["Power Whip", 16],
    ["Stealth Rock", 32],
  ]),
  mon("Infernape", "Simiofuego", 78, ["Fire", "Fighting"], "Focus Sash", [
    ["Close Combat", 8],
    ["Flare Blitz", 24],
    ["U-turn", 32],
    ["Mach Punch", 48],
  ]),
  mon("Togekiss", null, 74, ["Fairy", "Flying"], "Sitrus Berry", [
    ["Air Slash", 24],
    ["Dazzling Gleam", 16],
    ["Roost", 16],
    ["Thunder Wave", 32],
  ]),
];
const teamB = [
  mon("Tyranitar", "Godzilla", 80, ["Rock", "Dark"], "Assault Vest", [
    ["Stone Edge", 8],
    ["Crunch", 24],
    ["Earthquake", 16],
    ["Ice Punch", 24],
  ]),
  mon("Metagross", null, 79, ["Steel", "Psychic"], "Expert Belt", [
    ["Meteor Mash", 16],
    ["Zen Headbutt", 24],
    ["Bullet Punch", 48],
    ["Hammer Arm", 16],
  ]),
  mon("Volcarona", "Polilla", 77, ["Bug", "Fire"], "Leftovers", [
    ["Quiver Dance", 32],
    ["Fiery Dance", 16],
    ["Bug Buzz", 16],
    ["Giga Drain", 16],
  ]),
  mon("Starmie", "Estrellita", 76, ["Water", "Psychic"], "Choice Specs", [
    ["Hydro Pump", 8],
    ["Psychic", 16],
    ["Ice Beam", 16],
    ["Thunderbolt", 24],
  ]),
  mon("Excadrill", "Topo", 78, ["Ground", "Steel"], "Choice Band", [
    ["Earthquake", 16],
    ["Iron Head", 24],
    ["Rock Slide", 16],
    ["Rapid Spin", 64],
  ]),
  mon("Sylveon", null, 75, ["Fairy"], null, [
    ["Hyper Voice", 16],
    ["Wish", 16],
    ["Protect", 16],
    ["Light Screen", 48],
  ]),
];

// The hosted web can be checked too (POKEAPP_E2E_BASE_URL plus its API origin):
// every API request is still answered here, none reaches a server.
const api = process.env.POKEAPP_E2E_API_ORIGIN || "http://127.0.0.1:8000";

async function spectatorFixture(page: Page) {
  await fixture(page, false, api);
  await page.route(`${api}/**/team-preview*`, async (route) => {
    const request = route.request();
    if (request.method() !== "GET") return route.fallback();
    const params = new URL(request.url()).searchParams;
    const mode = params.get("mode") || "spectator";
    const first = params.get("trainer_id") || players[0].trainer_id;
    const second =
      params.get("second_trainer_id") ||
      players.find((p) => p.trainer_id !== first)!.trainer_id;
    await route.fulfill({
      headers: {
        "Access-Control-Allow-Origin":
          request.headers()["origin"] || "http://127.0.0.1:5173",
      },
      json: {
        season: overview.season,
        day: overview.days[0],
        mode,
        trainers: players.map(({ trainer_id, display_name, status }) => ({
          trainer_id,
          display_name,
          status,
        })),
        teams: (mode === "spectator" ? [first, second] : [first]).map(
          (id, index) => ({
            trainer_id: id,
            visibility: "public",
            provisional: null,
            unavailable_reason: null,
            lock: {
              locked_at: "2026-11-09T10:00:00Z",
              is_late: false,
              timing_status: "on_time",
              team: index === 0 ? teamA : teamB,
            },
          }),
        ),
      },
    });
  });
}

// Everything a spectator must read on each card: nickname, species, level,
// item and the four moves with their PP, for both teams and in order.
async function expectFullTeams(page: Page) {
  for (const [side, team] of [
    [".matchup-left", teamA],
    [".matchup-right", teamB],
  ] as const) {
    const cards = page.locator(`${side} .battle-pokemon`);
    await expect(cards).toHaveCount(6);
    for (const [index, pokemon] of team.entries()) {
      const card = cards.nth(index);
      await expect(card.locator(".matchup-sprite img")).toBeVisible();
      await expect(card.locator(".matchup-species")).toContainText(
        `Nv. ${pokemon.level}`,
      );
      await expect(card.locator(".held-item")).toBeVisible();
      if (!pokemon.item)
        await expect(card.locator(".held-item")).toHaveText("Sin objeto");
      await expect(card.locator(".move-button small")).toHaveText(
        pokemon.moves.map(({ pp }) => `${pp} PP`),
      );
      for (const pp of await card.locator(".move-button small").all())
        await expect(pp).toBeVisible();
    }
  }
  await expect(page.locator(".matchup-left strong").first()).toHaveText(
    "Tiburón",
  );
  await expect(
    page.locator(".matchup-left .matchup-species").first(),
  ).toHaveText("Garchomp · Nv. 78");
  await expect(page.locator(".matchup-left .held-item").first()).toHaveText(
    "Pañuelo Elección",
  );
  await expect(
    page.locator(".matchup-right .battle-pokemon").nth(4).locator(".move-name"),
  ).toHaveText(["Terremoto", "Cabeza de Hierro", "Avalancha", "Giro Rápido"]);
  // Spectator reads are public: no private field is ever drawn.
  await expect(page.locator(".spectator-matchup .battle-private")).toHaveCount(
    0,
  );
  await expect(page.locator(".spectator-matchup .battle-values")).toHaveCount(
    0,
  );
}

async function measure(page: Page) {
  return page.evaluate(() => {
    const cards = [
      ...document.querySelectorAll(".spectator-matchup .battle-pokemon"),
    ].map((card) => card.getBoundingClientRect());
    const scroller = document.scrollingElement!;
    // Any text that does not fit its box (cut, ellipsis or spilling out).
    const clipped = [
      ...document.querySelectorAll(
        ".spectator-matchup .battle-pokemon :is(strong, .matchup-species, .held-item, .move-name, small)",
      ),
    ]
      .filter(
        (el) =>
          el.scrollWidth > el.clientWidth + 1 ||
          el.scrollHeight > el.clientHeight + 1,
      )
      .map(
        (el) =>
          `${el.className} "${el.textContent}" ${el.scrollWidth}x${el.scrollHeight} in ${el.clientWidth}x${el.clientHeight}`,
      );
    // Two cards of the same team must never overlap.
    const overlaps = cards.filter((a, i) =>
      cards.some(
        (b, j) =>
          i !== j &&
          a.left < b.right - 1 &&
          b.left < a.right - 1 &&
          a.top < b.bottom - 1 &&
          b.top < a.bottom - 1,
      ),
    ).length;
    return {
      bottom: Math.max(...cards.map((r) => r.bottom)),
      right: Math.max(...cards.map((r) => r.right)),
      top: Math.min(...cards.map((r) => r.top)),
      innerHeight,
      innerWidth,
      scrollHeight: scroller.scrollHeight,
      scrollWidth: scroller.scrollWidth,
      clipped,
      overlaps,
    };
  });
}

async function openSpectator(
  page: Page,
  size: { width: number; height: number },
) {
  await page.setViewportSize(size);
  await spectatorFixture(page);
  await login(page);
  await navigate(page, "Batallas");
  await expect(page.locator(".spectator-matchup .battle-pokemon")).toHaveCount(
    12,
  );
  await expect(page.locator(".spectator-matchup .move-button")).toHaveCount(48);
  // Every sprite settles before measuring (lazy ones below the fold too).
  await page.evaluate(async () => {
    for (const image of document.querySelectorAll(".spectator-matchup img")) {
      image.scrollIntoView({ block: "center" });
      await new Promise((resolve) => setTimeout(resolve, 40));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForFunction(() =>
    [
      ...document.querySelectorAll<HTMLImageElement>(".spectator-matchup img"),
    ].every((image) => image.complete),
  );
}

for (const size of [
  { width: 1650, height: 900 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
  { width: 1366, height: 768 },
]) {
  test(`spectator shows both full teams without scroll at ${size.width}×${size.height}`, async ({
    page,
  }, info) => {
    await openSpectator(page, size);
    await expectFullTeams(page);
    await page.screenshot({
      path: info.outputPath(`spectator-${size.width}x${size.height}.png`),
    });
    const layout = await measure(page);
    expect(layout.top).toBeGreaterThanOrEqual(0);
    expect(layout.bottom).toBeLessThanOrEqual(layout.innerHeight);
    expect(layout.right).toBeLessThanOrEqual(layout.innerWidth);
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth + 1);
    expect(layout.scrollHeight).toBeLessThanOrEqual(layout.innerHeight + 1);
    expect(layout.clipped).toEqual([]);
    expect(layout.overlaps).toBe(0);
  });
}

// Smaller screens may scroll the page, never sideways, never inside a team,
// and never cut a name, item, move or PP.
for (const size of [
  { width: 1024, height: 768 },
  { width: 390, height: 844 },
]) {
  test(`spectator adapts without clipping at ${size.width}×${size.height}`, async ({
    page,
  }, info) => {
    await openSpectator(page, size);
    await expectFullTeams(page);
    await page.screenshot({
      path: info.outputPath(`spectator-${size.width}x${size.height}.png`),
      fullPage: true,
    });
    const layout = await measure(page);
    expect(layout.right).toBeLessThanOrEqual(layout.innerWidth);
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth + 1);
    expect(layout.clipped).toEqual([]);
    expect(layout.overlaps).toBe(0);
    const roster = await page
      .locator(".matchup-roster")
      .evaluateAll((lists) =>
        lists.map((l) => l.scrollHeight - l.clientHeight),
      );
    expect(roster.every((extra) => extra <= 1)).toBe(true);
  });
}

// Owner 2026-11-18: on a big screen the face-off grows with it, and its text
// reads comfortably (no magnifier). Computed sizes in CSS pixels.
async function sizes(page: Page) {
  return page.evaluate(() => {
    const px = (selector: string, property: "fontSize" | "width") =>
      Math.min(
        ...[...document.querySelectorAll(`.spectator-matchup ${selector}`)].map(
          (el) =>
            property === "width"
              ? el.getBoundingClientRect().width
              : parseFloat(getComputedStyle(el).fontSize),
        ),
      );
    return {
      card: px(".battle-pokemon", "width"),
      sprite: px(".matchup-sprite", "width"),
      name: px(".matchup-identity strong", "fontSize"),
      species: px(".matchup-species", "fontSize"),
      item: px(".held-item", "fontSize"),
      move: px(".move-name", "fontSize"),
      pp: px(".move-button small", "fontSize"),
    };
  });
}

test("the face-off grows with a big screen and reads without a magnifier", async ({
  page,
}) => {
  await openSpectator(page, { width: 1650, height: 900 });
  const reference = await sizes(page);
  await page.setViewportSize({ width: 2560, height: 1440 });
  await expect
    .poll(async () => (await sizes(page)).card)
    .toBeGreaterThan(reference.card * 1.4);
  const big = await sizes(page);
  expect(big.sprite).toBeGreaterThanOrEqual(100);
  expect(big.name).toBeGreaterThanOrEqual(21);
  expect(big.species).toBeGreaterThanOrEqual(15);
  expect(big.item).toBeGreaterThanOrEqual(15);
  expect(big.move).toBeGreaterThanOrEqual(16);
  expect(big.pp).toBeGreaterThanOrEqual(12.5);
  // The reference screen never shrinks below the previous sizes.
  expect(reference.move).toBeGreaterThanOrEqual(11.5);
  expect(reference.species).toBeGreaterThanOrEqual(10.5);
  expect(reference.name).toBeGreaterThanOrEqual(14.4);
});

// A move's details open inside their own card, under the move: they never
// paint over another card, the card's other moves or the other team.
for (const size of [
  { width: 2560, height: 1440 },
  { width: 1650, height: 900 },
]) {
  test(`a move's details cover nothing at ${size.width}×${size.height}`, async ({
    page,
  }, info) => {
    await openSpectator(page, size);
    for (const [label, side, index] of [
      ["Ver Paz Mental", ".matchup-left", 2],
      ["Ver Pantalla de Luz", ".matchup-right", 5],
    ] as const) {
      const card = page.locator(`${side} .battle-pokemon`).nth(index);
      await card.getByRole("button", { name: label }).click();
      const details = card.locator(".move-expansion");
      await expect(details).toContainText("Referencia Pokémon X/Y");
      await expect(details).toContainText("Potencia");
      await expect(details).toBeInViewport({ ratio: 1 });
      await page.screenshot({
        path: info.outputPath(
          `spectator-move-${index}-${size.width}x${size.height}.png`,
        ),
        animations: "disabled",
      });
      const result = await details.evaluate((panel) => {
        const box = panel.getBoundingClientRect();
        const own = panel.closest(".battle-pokemon")!;
        const ownBox = own.getBoundingClientRect();
        const hits = (a: DOMRect, b: DOMRect) =>
          a.left < b.right - 1 &&
          b.left < a.right - 1 &&
          a.top < b.bottom - 1 &&
          b.top < a.bottom - 1;
        // Inside its own card, over no other card.
        const inside =
          box.left >= ownBox.left - 1 &&
          box.right <= ownBox.right + 1 &&
          box.top >= ownBox.top - 1 &&
          box.bottom <= ownBox.bottom + 1;
        const covered = [
          ...document.querySelectorAll(".spectator-matchup .battle-pokemon"),
        ].filter((card) => card !== own && hits(box, card.getBoundingClientRect()))
          .length;
        // Every move button of the page is still reachable where it is drawn.
        const hidden = [
          ...document.querySelectorAll<HTMLElement>(
            ".spectator-matchup .move-button",
          ),
        ].filter((button) => {
          const r = button.getBoundingClientRect();
          if (r.bottom < 0 || r.top > innerHeight) return false;
          const hit = document.elementFromPoint(
            r.left + r.width / 2,
            r.top + r.height / 2,
          );
          return !hit || !button.contains(hit);
        }).length;
        return { inside, covered, hidden };
      });
      expect(result).toEqual({ inside: true, covered: 0, hidden: 0 });
      const layout = await measure(page);
      expect(layout.overlaps).toBe(0);
      expect(layout.clipped).toEqual([]);
      expect(layout.scrollWidth).toBeLessThanOrEqual(layout.innerWidth + 1);
      // The owner's screen keeps everything in view even with a move open.
      if (size.width >= 2560)
        expect(layout.scrollHeight).toBeLessThanOrEqual(
          layout.innerHeight + 1,
        );
      await page.keyboard.press("Escape");
      await expect(details).toHaveCount(0);
    }
  });
}
