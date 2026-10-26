// Build the web against the local synthetic API, then start the preview servers.
// Output goes to dist-preview/ (git-ignored); the deployable dist/ is untouched.
process.env.VITE_API_BASE_URL = "http://127.0.0.1:4174";
const { build } = await import("vite");
if (!process.argv.includes("--no-build"))
  await build({
    mode: "preview",
    logLevel: "warn",
    build: { outDir: "dist-preview", emptyOutDir: true },
  });
await import("./server.mjs");
