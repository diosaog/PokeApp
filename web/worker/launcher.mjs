import launcher from "../launcher-release.json" with { type: "json" };

const filename = "PokeApp-Launcher-Setup.exe";
export const artifactKey = `windows/${launcher.version}/${filename}`;
export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== "/launcher/download")
      return env.ASSETS.fetch(request);
    if (!["GET", "HEAD"].includes(request.method))
      return new Response(null, {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    // Resolve only the committed version, never a client-supplied bucket path.
    const object =
      request.method === "HEAD"
        ? await env.LAUNCHER_RELEASES.head(artifactKey)
        : await env.LAUNCHER_RELEASES.get(artifactKey);
    if (!object)
      return new Response("Descarga temporalmente no disponible", {
        status: 503,
        headers: { "Cache-Control": "no-store" },
      });
    return new Response(request.method === "HEAD" ? null : object.body, {
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": `attachment; filename="${filename}"`,
        "Content-Length": String(object.size),
        "Cache-Control": "public, max-age=300",
        "X-Content-Type-Options": "nosniff",
        ETag: object.httpEtag,
      },
    });
  },
};
