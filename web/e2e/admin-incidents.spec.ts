import { test, expect, type Page } from "@playwright/test";
import { fixture, login, navigate, sid } from "./fixtures";

// Phase 28: the admin console in three areas and the incident center, with
// synthetic data. Every command waits for the server's receipt.
const api = "http://127.0.0.1:8000";
const incidents = `/v1/admin/seasons/${sid}/incidents`;

function overview(cancelled: boolean) {
  return {
    season_id: sid,
    season_status: "active",
    wallets: [
      {
        trainer_id: "t3",
        display_name: "Marcos",
        status: "active",
        balance: 12,
      },
      {
        trainer_id: "t4",
        display_name: "Elena",
        status: "active",
        balance: 40,
      },
    ],
    purchases: [
      {
        id: "11111111-1111-4111-8111-111111111111",
        trainer_id: "t3",
        display_name: "Marcos",
        item_name: "Escudo Pokémon",
        item_code: "blindar_pokemon",
        total_price: 30,
        status: cancelled ? "cancelled" : "pending",
        acquisition_type: "paid",
        purchased_at: "2026-10-20T10:00:00Z",
        linked_operation: false,
        cancellable: !cancelled,
        refundable: false,
      },
      {
        id: "22222222-2222-4222-8222-222222222222",
        trainer_id: "t4",
        display_name: "Elena",
        item_name: "Robar Pokémon",
        item_code: "robar_pokemon",
        total_price: 50,
        status: "pending",
        acquisition_type: "paid",
        purchased_at: "2026-10-21T10:00:00Z",
        linked_operation: true,
        cancellable: false,
        refundable: false,
      },
    ],
    robberies: [
      {
        authorization_id: "33333333-3333-4333-8333-333333333333",
        purchase_id: "22222222-2222-4222-8222-222222222222",
        requester: "Elena",
        donor: "Marcos",
        state: "COMPETITIVELY_ADJUDICATED",
        source_obligation: "DONOR_PHYSICAL_PENDING",
        destination_obligation: "RECIPIENT_PHYSICAL_PENDING",
        created_at: "2026-10-21T10:00:00Z",
      },
    ],
    history: cancelled
      ? [
          {
            operation_id: "44444444-4444-4444-8444-444444444444",
            kind: "purchase_cancel",
            actor: "Antonio",
            target: "Marcos",
            purchase_id: "11111111-1111-4111-8111-111111111111",
            amount: 30,
            reason: "Compra duplicada",
            status: "cancelled",
            created_at: "2026-10-27T10:00:00Z",
          },
        ]
      : [],
  };
}

async function console_(page: Page) {
  const posts: { path: string; body: unknown; key?: string }[] = [];
  let cancelled = false;
  await fixture(page);
  await page.route(`${api}${incidents}**`, async (route) => {
    const request = route.request();
    const headers = {
      "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
      "Access-Control-Allow-Headers":
        "authorization,content-type,idempotency-key",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    };
    if (request.method() === "OPTIONS")
      return route.fulfill({ status: 204, headers });
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST") {
      posts.push({
        path,
        body: request.postDataJSON(),
        key: request.headers()["idempotency-key"],
      });
      cancelled = true;
      return route.fulfill({
        status: 200,
        headers,
        json: {
          operation_id: request.headers()["idempotency-key"],
          kind: "purchase_cancel",
          season_id: sid,
          trainer_id: "t3",
          purchase_id: "11111111-1111-4111-8111-111111111111",
          status: "cancelled",
          amount: 30,
          ledger_id: "55555555-5555-4555-8555-555555555555",
          balance_after: 42,
          replayed: false,
        },
      });
    }
    return route.fulfill({ status: 200, headers, json: overview(cancelled) });
  });
  await login(page);
  await navigate(page, "Administración");
  return posts;
}

for (const width of [1440, 390]) {
  test(`three admin areas and a reasoned cancellation at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const posts = await console_(page);
    const areas = page.getByRole("navigation", {
      name: "Áreas de administración",
    });
    await expect(areas.getByRole("button")).toHaveCount(3);
    // The League tools keep their tabs inside the first area.
    await expect(
      page.getByRole("tab", { name: "Configuración", exact: true }),
    ).toBeVisible();
    await areas.getByRole("button", { name: /Economía e incidencias/ }).click();
    await expect(
      page.getByText("Vinculada a una operación de partida"),
    ).toBeVisible();
    await expect(page.getByText("Robo adjudicado · definitivo")).toBeVisible();
    await expect(
      page.getByText(
        "Retirada pendiente en el origen · Entrega pendiente en el destino",
      ),
    ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`incidents-${width}.png`),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Cancelar compra" });
    await expect(dialog).toContainText("12 → 42 PK₽");
    await dialog
      .getByLabel("Motivo (queda en el historial)")
      .fill("Compra duplicada");
    await dialog.getByRole("checkbox").check();
    await page.screenshot({ path: info.outputPath(`cancel-${width}.png`) });
    await dialog.getByRole("button", { name: "Confirmar cancelación" }).click();
    await expect(dialog).toBeHidden();
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe(
      `${incidents}/purchases/11111111-1111-4111-8111-111111111111`,
    );
    expect(posts[0].body).toEqual({
      action: "cancel",
      reason: "Compra duplicada",
    });
    expect(posts[0].key).toMatch(/^[0-9a-f-]{36}$/);
    // The console re-reads after the receipt: the history shows it.
    await expect(page.getByText("Compra cancelada")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await areas.getByRole("button", { name: /Cuentas y sistema/ }).click();
    await expect(
      page.getByRole("heading", { name: "Estado del sistema" }),
    ).toBeVisible();
    await page.screenshot({
      path: info.outputPath(`accounts-${width}.png`),
      fullPage: true,
    });
  });
}
