import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { LauncherDownload } from "./launcher-download";
import launcher from "../../launcher-release.json";

test("Save downloads the current version directly, without an intermediate route", () => {
  render(<LauncherDownload />);
  const link = screen.getByRole("link", { name: "Descargar Launcher" });
  expect(link).toHaveAttribute("href", "/launcher/download");
  expect(link).toHaveAttribute("download", "PokeApp-Launcher-Setup.exe");
  expect(
    screen.getByText(`Windows 10/11 · v${launcher.version}`),
  ).toBeVisible();
});
