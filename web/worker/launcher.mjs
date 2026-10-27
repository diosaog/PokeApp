import launcher from "../launcher-release.json" with { type: "json" };

const filename = "PokeApp-Launcher-Setup.exe";
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

const unavailable = (status, text) =>
  new Response(text, { status, headers: { "Cache-Control": "no-store" } });

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    const update = pathname.startsWith("/launcher/updates/")
      ? updateKey(pathname)
      : null;
    if (pathname.startsWith("/launcher/updates/") && !update)
      return unavailable(404, "No encontrado");
    if (pathname !== "/launcher/download" && !update)
      return env.ASSETS.fetch(request);
    if (!["GET", "HEAD"].includes(request.method))
      return new Response(null, {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    // Resolve only the committed version or a validated channel key.
    const key = update ? update.key : artifactKey;
    const object =
      request.method === "HEAD"
        ? await env.LAUNCHER_RELEASES.head(key)
        : await env.LAUNCHER_RELEASES.get(key);
    if (!object)
      return update?.kind === "feed"
        ? unavailable(404, "Sin versiones publicadas")
        : unavailable(503, "Descarga temporalmente no disponible");
    if (update?.kind === "feed")
      return new Response(request.method === "HEAD" ? null : object.body, {
        headers: {
          "Content-Type": "application/json",
          "Content-Length": String(object.size),
          // A new release must be seen at the next check.
          "Cache-Control": "no-store",
          "X-Content-Type-Options": "nosniff",
          ETag: object.httpEtag,
        },
      });
    return new Response(request.method === "HEAD" ? null : object.body, {
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": `attachment; filename="${update ? update.file : filename}"`,
        "Content-Length": String(object.size),
        // Versioned objects never change: published once, kept for rollback.
        "Cache-Control": update
          ? "public, max-age=86400, immutable"
          : "public, max-age=300",
        "X-Content-Type-Options": "nosniff",
        ETag: object.httpEtag,
      },
    });
  },
};
