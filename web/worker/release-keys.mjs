// Release object keys. Kept apart from the Worker entry: workerd reads every
// named export of the main module as an entrypoint and refuses a string.
import launcher from "../launcher-release.json" with { type: "json" };

export const filename = "PokeApp-Launcher-Setup.exe";
export const artifactKey = `windows/${launcher.version}/${filename}`;

// Update channel (read only). The signed manifest is the authority: the
// Launcher verifies it against its pinned public key, so these routes only
// hand out bytes. Keys are built from a fixed channel name and a validated
// version, never from a client-supplied bucket path; there is no listing or
// upload route.
const channels = {
  stable: { folder: "windows", file: "PokeApp-Launcher-Setup.exe" },
  private: { folder: "private", file: "PokeApp-Launcher-Private-Setup.exe" },
};
const version = /^\d{1,4}\.\d{1,4}\.\d{1,4}(?:-[0-9A-Za-z.]{1,32})?$/;
export function updateKey(pathname) {
  const feed = /^\/launcher\/updates\/(stable|private)\.json$/.exec(pathname);
  if (feed) return { key: `updates/${feed[1]}.json`, kind: "feed" };
  const binary = /^\/launcher\/updates\/(stable|private)\/([^/]+)\.exe$/.exec(
    pathname,
  );
  if (!binary || !version.test(binary[2]) || binary[2].includes(".."))
    return null;
  const { folder, file } = channels[binary[1]];
  return {
    key: `${folder}/${binary[2]}/${file}`,
    kind: "installer",
    file,
  };
}
