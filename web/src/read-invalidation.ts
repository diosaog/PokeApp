/** Read dependencies of accepted commands. Query keys retain viewer and full mode. */
export function affectedRead(command: string, read: string): boolean {
  const match = command.match(/^\/v1\/(?:admin\/)?seasons\/([^/?]+)(.*)$/);
  if (!match)
    return (
      command === "/v1/admin/seasons" && read === "/v1/read/seasons?offset=0"
    );
  const [, season, action] = match;
  const readSeason = read.match(
    /^\/v1\/(?:read\/|admin\/)?seasons\/([^/?]+)(.*)$/,
  );
  const lifecycle =
    /\/(open|close|cancel|finish|archive|discard|activate|prepare|participants|initial-assignment|initial-divisions|correct)(\/|$|-)/.test(
      action,
    );
  if (read === "/v1/read/seasons?offset=0")
    return lifecycle || action === "/name";
  if (read.startsWith("/v1/read/hall"))
    return action === "/archive" || action.includes("/cups/");
  if (!readSeason || readSeason[1] !== season) return false;
  const target = readSeason[2].split("?")[0];
  const is = (...paths: string[]) =>
    paths.some((p) => target === p || target.startsWith(p + "/"));
  if (action.includes("/cups")) return is("/cups", "/overview");
  if (action.includes("/team-lock"))
    return is("/overview", "/team-preview", "/scouting", "/setup");
  if (action === "/rules" || action.includes("/config-versions"))
    return is("/rules", "/setup", "/initial-assignment", "/overview");
  if (action === "/name")
    return is("/setup", "/overview", "/league", "/team-preview", "/scouting");
  if (lifecycle)
    return is(
      "/setup",
      "/rules",
      "/overview",
      "/league",
      "/matchdays",
      "/championship",
      "/initial-assignment",
      "/team-preview",
      "/scouting",
      "/shop",
      "/inventory",
      "/wipe-revivals",
    );
  if (action.includes("/championship/")) return is("/championship", "/setup");
  // Economic commands can change deaths/eligibility as well as the wallet.
  if (
    action.includes("/shop") ||
    action.includes("/trials") ||
    action.includes("/wipe-revivals") ||
    action.includes("/progress")
  )
    return is(
      "/shop",
      "/inventory",
      "/league",
      "/overview",
      "/matchdays",
      "/championship",
      "/initial-assignment",
      "/wipe-revivals",
      "/progress",
      "/trials",
      "/setup",
    );
  if (action.endsWith("/results"))
    return is("/league", "/overview", "/matchdays", "/championship", "/setup");
  return is("/setup");
}

export function invalidationFor(
  viewer: string | undefined,
  command: string,
  extra: readonly string[] = [],
) {
  return (query: { queryKey: readonly unknown[] }) =>
    query.queryKey[0] === viewer &&
    (affectedRead(command, String(query.queryKey[1])) ||
      extra.includes(String(query.queryKey[1])));
}
