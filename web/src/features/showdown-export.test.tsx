import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { ApiError } from "../api/client";
import { TopNotices, dismissNotice } from "../ui";
import { COPIED, ShowdownExport } from "./showdown-export";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  invalidate: vi.fn(),
}));
vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: { request: mocks.request },
}));
vi.mock("../state", () => ({
  queries: { invalidateQueries: mocks.invalidate },
  useViewer: () => "owner",
  useApp: () => ({ season: "season", me: { trainer_id: "owner" } }),
}));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});

const save = {
  id: "save-1",
  parser_status: "parsed",
  parser_version: "v",
  uploaded_at: "2026-11-03T20:00:00Z",
  game: "Y",
};
const TEXT =
  "Crawdaunt (M) @ Mystic Water\nAbility: Hyper Cutter\nLevel: 95\nEVs: 1 HP / 1 Atk / 1 Def / 1 SpA / 1 SpD / 1 Spe\nNaive Nature\nIVs: 2 HP / 22 Atk / 17 Def / 23 SpA / 25 SpD / 21 Spe\n- Crunch\n";
const exported = (changes = {}) => ({
  save_id: "save-1",
  uploaded_at: "2026-11-03T20:00:00+00:00",
  game: "Y",
  text: TEXT,
  count: 1,
  warnings: [],
  ...changes,
});
const writeText = vi.fn();
beforeEach(() => {
  vi.clearAllMocks();
  mocks.request.mockResolvedValue(exported());
  writeText.mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
});
afterEach(() => {
  for (const key of ["showdown-export", "showdown-export-warnings"])
    dismissNotice(key);
  cleanup();
});

function view(personal = true) {
  return render(
    <>
      <TopNotices />
      <ShowdownExport save={save} personal={personal} />
    </>,
  );
}
const button = () => screen.getByRole("button", { name: "Generar Poképaste" });

it("generates nothing until the trainer asks", async () => {
  const { rerender } = view();
  rerender(
    <>
      <TopNotices />
      <ShowdownExport
        save={{ ...save, uploaded_at: "2026-11-03T21:00:00Z" }}
        personal
      />
    </>,
  );
  await act(async () => {});
  expect(mocks.request).not.toHaveBeenCalled();
  expect(writeText).not.toHaveBeenCalled();
});

it("copies the current personal party once and says so", async () => {
  view();
  fireEvent.click(button());
  fireEvent.click(button()); // a second press while working is ignored
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(TEXT));
  expect(mocks.request).toHaveBeenCalledExactlyOnceWith("/v1/me/pc/showdown");
  expect(await screen.findByText(COPIED)).toBeVisible();
  expect(COPIED).toBe("Equipo copiado. Ya puedes pegarlo en Pokémon Showdown.");
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("uses the League save when that is the one on screen", async () => {
  view(false);
  fireEvent.click(button());
  await waitFor(() => expect(writeText).toHaveBeenCalled());
  expect(mocks.request).toHaveBeenCalledWith(
    "/v1/read/seasons/season/pc/showdown",
  );
});

it("offers the text to copy by hand when the clipboard is refused, without claiming a copy", async () => {
  writeText.mockRejectedValueOnce(
    new DOMException("denied", "NotAllowedError"),
  );
  view();
  fireEvent.click(button());
  const area = await screen.findByRole("textbox", {
    name: "Equipo en formato Pokémon Showdown",
  });
  expect(area).toHaveValue(TEXT);
  expect(area).toHaveAttribute("readonly");
  expect(screen.queryByText(COPIED)).toBeNull();
  expect(screen.getByText(/Custom Game/)).toBeVisible();
  // The dialog's own button is a fresh gesture.
  fireEvent.click(screen.getByRole("button", { name: "Copiar" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledTimes(2));
  expect(await screen.findAllByText(COPIED)).not.toHaveLength(0);
});

it("without any clipboard API it still shows the text, not a success", async () => {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: undefined,
  });
  view();
  fireEvent.click(button());
  expect(
    await screen.findByRole("textbox", {
      name: "Equipo en formato Pokémon Showdown",
    }),
  ).toHaveValue(TEXT);
  expect(screen.queryByText(COPIED)).toBeNull();
});

it("never copies a team from another sync than the one displayed", async () => {
  mocks.request.mockResolvedValue(
    exported({ uploaded_at: "2026-11-03T20:05:00Z" }),
  );
  view();
  fireEvent.click(button());
  expect(await screen.findByText(/Tu partida acaba de cambiar/)).toBeVisible();
  expect(writeText).not.toHaveBeenCalled();
  expect(mocks.invalidate).toHaveBeenCalledOnce();
});

it("explains what could not be represented", async () => {
  mocks.request.mockResolvedValue(
    exported({
      warnings: [
        { code: "item_not_in_showdown", slot: 4, detail: "Everstone" },
        { code: "gender_unavailable", slot: 2, detail: "Pikachu" },
      ],
    }),
  );
  view();
  fireEvent.click(button());
  expect(
    await screen.findByText(
      /Equipo 4: Everstone no existe en Showdown; se exporta sin objeto\. Equipo 2:/,
    ),
  ).toBeVisible();
  expect(writeText).toHaveBeenCalledWith(TEXT);
});

it("shows the server's reason when there is no team to export", async () => {
  mocks.request.mockRejectedValue(new ApiError(409, "SHOWDOWN_TEAM_EMPTY"));
  view();
  fireEvent.click(button());
  expect(
    await screen.findByText(/no tiene Pokémon en el equipo para exportar/),
  ).toBeVisible();
  expect(writeText).not.toHaveBeenCalled();
  expect(button()).toBeEnabled();
});
