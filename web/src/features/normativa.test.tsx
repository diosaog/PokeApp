import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { NormativaPage } from "./normativa";
import { chapters, netText, netTenths, stretches } from "./normativa-content";

afterEach(cleanup);
const page = () =>
  render(
    <MemoryRouter>
      <NormativaPage />
    </MemoryRouter>,
  );
const text = () => document.body.textContent ?? "";

describe("NET arithmetic", () => {
  it("matches the official examples in exact tenths", () => {
    expect(netTenths(3, 2, 0)).toBe(28);
    expect(netText(3, 2, 0)).toBe("2,8");
    expect(netText(1, 1, 1)).toBe("0,7");
    expect(netText(0, 3, 0)).toBe("−0,3");
    expect(netText(0, 0, 0)).toBe("0");
    expect(netText(4, 0, 0)).toBe("4");
    // A sum that binary floats get wrong (0.1 * 3 = 0.30000000000000004).
    expect(netText(1, 3, 0)).toBe("0,7");
  });
});

describe("Normativa", () => {
  it("has a heading and an index entry for all seven chapters", () => {
    page();
    expect(chapters).toHaveLength(7);
    const index = screen.getByRole("navigation", {
      name: "Capítulos de la Normativa",
    });
    for (const chapter of chapters) {
      expect(
        screen.getByRole("heading", { level: 2, name: chapter.title }),
      ).toBeTruthy();
      expect(
        within(index)
          .getByRole("link", { name: new RegExp(chapter.title) })
          .getAttribute("href"),
      ).toBe(`#nv-${chapter.id}`);
    }
  });

  it("covers every section of the original document", () => {
    page();
    const body = text();
    for (const rule of [
      // 1.1 Generales
      "caja de muertos",
      "esclavo de MO",
      "primer Pokémon salvaje de cada ruta o zona",
      "deben llevar mote",
      // 1.2 Adicionales
      "Cláusula de duplicados",
      "línea evolutiva",
      "Cláusula de legendarios",
      "sea o no el primer encuentro",
      "no cuenta como el primero de esa ruta",
      "Forzar la aparición de shinies",
      "abandonas el combate",
      "evoluciones alternativas",
      "Eevee",
      "objetos de combate u objetos curativos",
      "Cada objeto solo puede comprarse una vez",
      "Aarón no podrá buscar vacíos legales",
      "Las normas pueden editarse en cualquier momento",
      // 2 Límite de nivel
      "Alto Mando",
      "Tileo, Trazena, Malva y Narciso",
      "Dianta",
      "monedas por cada medalla",
      "por vencer a la Campeona",
      "siguiente líder",
      "delante del líder de gimnasio",
      "ajustar un Pokémon al nivel de tu equipo",
      "deberá guardarse en la caja",
      "puedes hacer reset",
      // 3 Tramos y combates
      "segundo líder",
      "cuarto líder",
      "sexta líder",
      "al acabar el juego",
      "lo marca el último líder del tramo",
      "antes de que se abra la jornada",
      // 4 Partida
      "en directo en el canal de Discord",
      "grupo de WhatsApp",
      "Caramelos Raros y Escamas Corazón ilimitados",
      "Vender estos objetos",
      // 5.3 Interacción
      "intercambiar Pokémon",
      "pseudo-legendarios",
      "un intercambio por cada tramo",
      "Incluir objetos en un intercambio",
      "combates de práctica",
      "cartas comodín",
      "hasta que todos los demás jugadores lo hayan sido también",
      "24 horas desde la captura",
    ])
      expect(body, rule).toContain(rule);
  });

  it("presents the current rules, not the replaced ones", () => {
    page();
    const body = text();
    for (const current of [
      "Una misma muerte nunca se penaliza dos veces",
      "Revivir un Pokémon no elimina la muerte registrada",
      "Los puntos NET acumulados determinan la clasificación general y el campeón",
      "Todos contra todos",
      "Combate de desempate 1v1",
      "Blindar Pokémon extra",
      "Robar Pokémon extra",
      "fuera de plazo",
    ])
      expect(body, current).toContain(current);
    expect(body).not.toMatch(/2 puntos por victoria/i);
    expect(body).not.toMatch(/un día antes/i);
    expect(body).not.toMatch(/palo por el culo/i);
    expect(body).not.toMatch(/antitrampas/i);
    expect(screen.getByText("+1")).toBeTruthy();
    expect(screen.getByText("−0,1")).toBeTruthy();
    expect(screen.getByText("−0,2")).toBeTruthy();
  });

  it("does not announce unavailable wildcards as available", () => {
    page();
    for (const name of ["Revivir Pokémon", "Robar Pokémon"]) {
      const card = screen
        .getByRole("heading", { level: 4, name })
        .closest("li")!;
      expect(card.textContent).toContain("Su uso aún no está activado");
      expect(card.textContent).not.toContain("Disponible");
    }
    const shield = screen
      .getByRole("heading", { level: 4, name: "Blindar Pokémon" })
      .closest("li")!;
    expect(shield.textContent).toContain("Disponible");
  });

  it("shows every level cap, with the four matchday levels", () => {
    page();
    expect(stretches.flatMap((s) => s.challenges.map((c) => c.level))).toEqual([
      14, 30, 38, 41, 44, 50, 58, 70, 78, 82,
    ]);
    expect(stretches.map((s) => s.cap)).toEqual([30, 41, 50, 82]);
    expect(
      [...document.querySelectorAll(".nv-level")].map((node) =>
        node.textContent?.replace("Límite de nivel ", ""),
      ),
    ).toEqual(["14", "30", "38", "41", "44", "50", "58", "70", "78", "82"]);
  });

  it("keeps the two NET examples and recalculates with the steppers", async () => {
    page();
    const body = text();
    expect(body).toContain("3 victorias y 2 muertes ordinarias");
    expect(body).toContain(
      "1 victoria, 1 muerte ordinaria y 1 muerte revivida tras wipe",
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Añadir victorias" }));
    await user.click(
      screen.getByRole("button", { name: "Añadir muertes ordinarias" }),
    );
    expect(document.querySelector(".nv-calc-result strong")?.textContent).toBe(
      "2,8",
    );
  });
});
