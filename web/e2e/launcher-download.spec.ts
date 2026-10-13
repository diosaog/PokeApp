import { test, expect } from "@playwright/test";
import { fixture, login, navigate } from "./fixtures";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

for (const width of [1365, 390]) {
  test(`Save direct Launcher download at ${width}px`, async ({ page }) => {
    const expectedHash = process.env.POKEAPP_EXPECTED_INSTALLER_SHA256;
    if (expectedHash) test.setTimeout(180000);
    await page.setViewportSize({ width, height: 844 });
    await fixture(page);
    await login(page);
    await navigate(page, "Saves y Launcher");
    const button = page.getByRole("link", { name: "Descargar Launcher" });
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute("href", "/launcher/download");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    if (!expectedHash)
      await page.route("**/launcher/download", (route) =>
        route.fulfill({
          body: Buffer.from("MZ-synthetic-download"),
          headers: {
            "Content-Type": "application/octet-stream",
            "Content-Disposition":
              'attachment; filename="PokeApp-Launcher-Setup.exe"',
          },
        }),
      );
    const downloadEvent = page.waitForEvent("download");
    await button.click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toBe("PokeApp-Launcher-Setup.exe");
    expect(await download.failure()).toBeNull();
    if (expectedHash) {
      const downloaded = await download.path();
      expect(downloaded).toBeTruthy();
      expect(
        createHash("sha256")
          .update(await readFile(downloaded!))
          .digest("hex"),
      ).toBe(expectedHash);
    }
    await expect(page).toHaveURL(/\/saves$/);
  });
}
