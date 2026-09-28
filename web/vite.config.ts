import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const base = process.env.VITE_API_BASE_URL || env.VITE_API_BASE_URL || "";
  let origin = "";
  if (base) {
    const url = new URL(base);
    if (
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      !["https:", "http:"].includes(url.protocol) ||
      (url.protocol === "http:" &&
        !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname))
    )
      throw new Error(
        "VITE_API_BASE_URL must be HTTPS (HTTP only for local validation).",
      );
    origin = url.origin;
  }
  if (command === "build" && !origin)
    throw new Error("Set the public VITE_API_BASE_URL before building.");
  return {
    plugins: [
      react(),
      {
        name: "pokeapp-delivery-headers",
        generateBundle() {
          this.emitFile({
            type: "asset",
            fileName: "_headers",
            source: `/*\n  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' ${origin}; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n  X-Frame-Options: DENY\n`,
          });
          this.emitFile({
            type: "asset",
            fileName: "build-config.json",
            source: JSON.stringify({ api_base_url: base, mode }),
          });
        },
      },
    ],
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      restoreMocks: true,
    },
  };
});
