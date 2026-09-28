// Synthetic browser fixtures only. Never bundled into the product or uploaded.
import { expect, type Page } from "@playwright/test";
export const sid = "10000000-0000-4000-8000-000000000001",
  tid = "10000000-0000-4000-8000-000000000002",
  pid = "10000000-0000-4000-8000-000000000003",
  day = "10000000-0000-4000-8000-000000000004",
  cid = "10000000-0000-4000-8000-000000000005",
  side = "10000000-0000-4000-8000-000000000006";
export const pokemon = {
  species: "Lucario",
  nickname: "Aura",
  level: 42,
  types: ["Lucha", "Acero"],
  moves: [
    { name: "Esfera aural", pp: 20 },
    { name: "Pulso umbrío", pp: 15 },
  ],
  item: "Vidasfera",
  ability: "Foco interno",
  nature: "Modesta",
  ivs: { hp: 31, atk: 20, defense: 25, spa: 31, spd: 28, spe: 30 },
  evs: { hp: 4, atk: 0, defense: 0, spa: 252, spd: 0, spe: 252 },
};
export const players = [
  {
    id: pid,
    trainer_id: tid,
    display_name: "Antonio",
    status: "active",
    badges_count: 6,
  },
  {
    id: "rival-player",
    trainer_id: "rival-trainer",
    display_name: "Lucía",
    status: "active",
    badges_count: 7,
  },
  {
    id: "p3",
    trainer_id: "t3",
    display_name: "Marcos",
    status: "active",
    badges_count: 4,
  },
  {
    id: "p4",
    trainer_id: "t4",
    display_name: "Elena",
    status: "active",
    badges_count: 5,
  },
];
export const overview = {
  points: players.map((p, i) => ({
    season_player_id: p.id,
    earned_points: String(30 - i * 4),
    points_reduction: "1.25",
    dead_points_penalty: "0.2",
    sanctioned_points: String(28.55 - i * 4),
    source_matchday_id: "old-day",
  })),
  season: {
    id: sid,
    name: "Liga Horizonte",
    status: "active",
    current_matchday_id: day,
  },
  players,
  days: [
    { id: day, number: 4, status: "open" },
    { id: "old-day", number: 3, status: "closed" },
  ],
  matches: [
    {
      id: "match",
      matchday_id: day,
      division_id: "division",
      player_a_id: pid,
      player_b_id: "rival-player",
      winner_id: null,
      status: "scheduled",
    },
  ],
  divisions: [{ id: "division", code: "A", name: "División A" }],
  memberships: [
    {
      season_player_id: pid,
      division_id: "division",
      effective_from_matchday_number: 1,
      effective_to_matchday_number: null,
      eligibility_ends_before_matchday_number: null,
    },
  ],
  snapshots: [
    {
      matchday_id: "old-day",
      revision: 1,
      closed_at: "2026-09-27T12:00:00Z",
      standings: players.map((p, i) => ({
        season_player_id: p.id,
        division: i < 2 ? "A" : "B",
        position: i + 1,
        division_position: (i % 2) + 1,
        points_awarded: 10 - i * 2,
        score: String(10 - i * 2),
      })),
    },
  ],
  locks: [
    {
      trainer_id: "rival-trainer",
      matchday_id: day,
      locked_at: "2026-09-28T12:00:00Z",
      is_late: false,
      public_team_snapshot: Array.from({ length: 6 }, () => pokemon),
    },
  ],
  balance: 128,
};
export const cup = {
  id: cid,
  season_id: sid,
  name: "Copa Equinoccio",
  format: "doubles",
  status: "active",
  revision: 4,
  rules_version: 1,
  swiss_rounds: 1,
  sides: [
    {
      id: side,
      name: "Dúo Aurora",
      seed: 1,
      status: "active",
      members: [
        { trainer_id: tid, season_player_id: pid, display_name: "Antonio" },
        {
          trainer_id: "rival-trainer",
          season_player_id: "rival-player",
          display_name: "Lucía",
        },
      ],
    },
    {
      id: "other-side",
      name: "Dúo Eclipse",
      seed: 2,
      status: "active",
      members: [
        { trainer_id: "t3", season_player_id: "p3", display_name: "Marcos" },
        { trainer_id: "t4", season_player_id: "p4", display_name: "Elena" },
      ],
    },
  ],
  rounds: [
    {
      number: 1,
      phase: "final",
      status: "open",
      eligible_side_ids: [side, "other-side"],
      matches: [
        {
          id: "cup-match",
          position: 1,
          a: side,
          b: "other-side",
          winner: null,
          status: "scheduled",
          score_a: null,
          score_b: null,
        },
      ],
    },
  ],
  standings: [],
  certificate_id: null,
  champion_side_id: null,
  finalist_side_id: null,
  checksum: null,
};
export async function fixture(page: Page) {
  const commands: {
    path: string;
    body: Record<string, unknown>;
    key: string | undefined;
  }[] = [];
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    const headers = {
      "Access-Control-Allow-Origin":
        request.headers()["origin"] || "http://127.0.0.1:5173",
      "Access-Control-Allow-Headers":
        "authorization,content-type,idempotency-key",
      "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
    };
    if (request.method() === "OPTIONS")
      return route.fulfill({ status: 204, headers });
    let result: unknown;
    if (path.endsWith("/pin-login"))
      result = {
        trainer_id: tid,
        auth_user_id: "user",
        session: {
          user_id: "user",
          access_token: "test-token",
          refresh_token: "test-refresh",
        },
      };
    else if (path === "/v1/me")
      result = {
        trainer_id: tid,
        display_name: "Antonio",
        is_admin: true,
        globally_enabled: true,
      };
    else if (request.method() !== "GET") {
      commands.push({
        path,
        body: request.postDataJSON(),
        key: request.headers()["idempotency-key"],
      });
      result = { operation_id: "receipt", replayed: false };
    } else if (path === "/v1/read/seasons")
      result = { items: [overview.season], next_offset: null };
    else if (path === "/v1/read/trainers")
      result = players.map((p) => ({
        id: p.trainer_id,
        display_name: p.display_name,
      }));
    else if (path.endsWith("/overview")) result = overview;
    else if (path.endsWith("/pc"))
      result = {
        save: {
          id: "save",
          parser_status: "parsed",
          parser_version: "fixture",
          uploaded_at: "2026-09-28T12:00:00Z",
        },
        status: "ready",
        pokemon: Array.from({ length: 12 }, (_, i) => ({
          location: i < 6 ? `Equipo · ${i + 1}` : `Caja 1 · ${i - 5}`,
          pokemon,
        })),
      };
    else if (path.endsWith("/inventory"))
      result = {
        purchases: [
          {
            id: "owned-purchase",
            shop_item_id: "item",
            item_name: "Escudo Pokémon",
            item_code: "blindar_pokemon",
            status: "pending",
            total_price: 30,
            purchased_at: "2026-09-28T12:00:00Z",
          },
        ],
        targets: [
          {
            pokemon_entity_id: "confirmed-entity",
            trainer_id: tid,
            location: "Equipo · 1",
            visibility: "own",
            pokemon,
          },
        ],
      };
    else if (path.endsWith("/trials/trial"))
      result = {
        id: "trial",
        season_id: sid,
        case_number: 1,
        revision: 2,
        title: "Revisión de resultado",
        description: "Decisión acordada en Discord.",
        status: "open",
        verdict: null,
        is_public: true,
        created_at: "2026-09-28T12:00:00Z",
        updated_at: "2026-09-28T12:00:00Z",
        resolved_at: null,
        sanctions: [],
        detail: {
          evidence: "Referencia del acuerdo",
          history: [
            {
              id: "history",
              revision: 1,
              operation: "create",
              actor_trainer_id: tid,
              created_at: "2026-09-28T12:00:00Z",
              previous_decision_id: null,
              details: {
                title: "Revisión de resultado",
                description: "Propuesta",
                is_public: true,
                evidence: "",
              },
              verdict: null,
              decision_summary: "",
              reason: "",
              sanctions: [],
            },
          ],
        },
      };
    else if (path.endsWith("/shop"))
      result = {
        balance: 128,
        items: [
          {
            id: "item",
            code: "blindar_pokemon",
            name: "Escudo Pokémon",
            category: "Protección",
            description: "Protege a un miembro de tu equipo.",
            base_price: 30,
          },
          {
            id: "item2",
            code: "revivir_pokemon",
            name: "Revivir",
            category: "Recuperación",
            description: "Una nueva oportunidad para seguir luchando.",
            base_price: 45,
          },
          {
            id: "item3",
            code: "robar_pokemon",
            name: "Robo Pokémon",
            category: "Estrategia",
            description: "Un movimiento inesperado puede cambiar la partida.",
            base_price: 60,
          },
        ],
        promotions: [],
      };
    else if (path.endsWith("/cups")) result = [cup];
    else if (path.endsWith("/cups/" + cid)) result = cup;
    else if (path === "/v1/read/hall")
      result = {
        items: [
          {
            id: "hall",
            season_id: sid,
            competition_type: "cup",
            champion_trainer_id: null,
            finalist_trainer_id: null,
            finalized_at: "2026-09-27T12:00:00Z",
            cup_id: cid,
            cup_certificate_id: "cert",
            champion_side_id: side,
            finalist_side_id: "other-side",
            cup_sides: cup.sides,
            cup_checksum: "fixture-checksum",
          },
        ],
        next_offset: null,
      };
    else if (path.endsWith("/trials"))
      result = {
        season_id: sid,
        cases: [
          {
            id: "trial",
            season_id: sid,
            case_number: 1,
            revision: 2,
            title: "Revisión de resultado",
            description:
              "Acuerdo pendiente de registrar tras la revisión en Discord.",
            status: "open",
            verdict: null,
            is_public: true,
            created_at: "2026-09-28T12:00:00Z",
            updated_at: "2026-09-28T12:00:00Z",
            resolved_at: null,
            sanctions: [],
            detail: null,
          },
        ],
      };
    else if (path.endsWith("/setup"))
      result = {
        season: { ...overview.season, started_at: "2026-09-25" },
        setup_revision: 7,
        roster_revision: 3,
        config_revision: 2,
        current_matchday_id: day,
        participants: players.map((p) => ({
          ...p,
          seed_order: 1,
          stats_ready: true,
        })),
        config_versions: [
          {
            id: "config",
            name: "Base",
            version_number: 1,
            effective_from_matchday: 1,
            total_matchdays: 8,
            division_sizes: { A: 2, B: 2 },
            movement_count: 1,
            scoring: { "1": 10, "2": 8, "3": 6, "4": 4 },
            coin_rewards: { "1": 8, "2": 6, "3": 4, "4": 2 },
            rules: { team_lock_required: true, last_b_gets_steal: false },
            roster_revision: 3,
            used: false,
            is_current: true,
          },
        ],
        divisions: [],
        memberships: [],
        first_matchday: null,
        readiness: { checks: {}, blocking_reasons: [], can_activate: false },
      };
    else if (path.endsWith("/matchdays/" + day))
      result = {
        season_id: sid,
        matchday_id: day,
        current_matchday_id: day,
        state: "open",
        revision: 2,
        results_revision: 3,
        snapshot_revision: 0,
        matches: overview.matches,
      };
    else
      return route.fulfill({
        status: 404,
        headers,
        json: { detail: { code: "FIXTURE_NOT_FOUND" } },
      });
    await route.fulfill({ status: 200, headers, json: result });
  });
  return commands;
}
export async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Entrenador", { exact: true }).fill("Antonio");
  await page.getByLabel("PIN", { exact: true }).fill("1234");
  await page.getByRole("button", { name: "Entrar a PokeApp" }).click();
  await expect(
    page.getByRole("heading", { name: "A por la siguiente, Antonio." }),
  ).toBeVisible();
}
export async function navigate(page: Page, label: string) {
  const menu = page.getByRole("button", { name: "Abrir navegación" });
  if (await menu.isVisible()) await menu.click();
  await page
    .getByRole("navigation", { name: "Principal" })
    .getByRole("link", { name: label, exact: true })
    .click();
}
