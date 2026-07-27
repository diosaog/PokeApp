import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { SessionProvider } from "@/state/sessionStore";

describe("flujo integrado de la app", () => {
  it("permite anadir reproductores en memoria", async () => {
    const user = userEvent.setup();
    render(
      <SessionProvider>
        <App />
      </SessionProvider>,
    );

    await user.click(screen.getByRole("button", { name: /Criadero/i }));
    await user.type(screen.getByLabelText("Mote"), "Eevee madre");
    await user.selectOptions(screen.getByTestId("pokemon-sex"), "female");
    const hpInput = screen.getAllByTestId("iv-hp")[0];
    if (!hpInput) {
      throw new Error("No se encontro el input de PS.");
    }
    await user.clear(hpInput);
    await user.type(hpInput, "31");
    await user.click(screen.getByRole("button", { name: /Guardar y anadir otro/i }));

    await user.type(screen.getByLabelText("Mote"), "Furret padre");
    await user.selectOptions(screen.getByTestId("species-select"), "furret");
    await user.selectOptions(screen.getByTestId("pokemon-sex"), "male");
    const specialDefenseInput = screen.getAllByTestId("iv-specialDefense")[0];
    if (!specialDefenseInput) {
      throw new Error("No se encontro el input de Defensa Especial.");
    }
    await user.clear(specialDefenseInput);
    await user.type(specialDefenseInput, "31");
    await user.click(screen.getByRole("button", { name: /Guardar y anadir otro/i }));

    expect(screen.getByText(/2 Pokemon en memoria/i)).toBeInTheDocument();
    expect(screen.getByText("Eevee madre")).toBeInTheDocument();
    expect(screen.getByText("Furret padre")).toBeInTheDocument();
  });
});
