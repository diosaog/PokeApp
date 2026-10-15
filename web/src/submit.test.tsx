import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { Submit } from "./ui";
afterEach(cleanup);
it("unavailable actions are disabled without pretending to be in progress", () => {
  const view = render(
    <Submit pending={false} disabled>
      Guardar
    </Submit>,
  );
  expect(screen.getByRole("button")).toBeDisabled();
  expect(document.querySelector(".spin")).toBeNull();
  view.rerender(<Submit pending>Guardar</Submit>);
  expect(screen.getByRole("button")).toHaveAttribute("aria-busy", "true");
  expect(document.querySelector(".spin")).not.toBeNull();
});
