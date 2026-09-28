import { defineRailway, project, service, preserve } from "railway/iac";

export default defineRailway(() => project("PokeApp V2", {
  resources: [service("pokeapp-api", {
    healthcheck: "/health",
    healthcheckTimeout: 120,
    replicas: 1,
    env: {
      PORT: "8000",
      POKEAPP_V2_SUPABASE_URL: "https://uwleqeuzsveqlugugzba.supabase.co",
      POKEAPP_V2_SUPABASE_ANON_KEY: preserve(),
      POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY: preserve(),
      POKEAPP_AUTH_PIN_PEPPER: preserve(),
      POKEAPP_API_CORS_ORIGINS: "https://pokeapp-web.pokeapp-v2.workers.dev",
    },
  })],
}));
