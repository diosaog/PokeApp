import {
  createContext,
  useCallback,
  useEffect,
  useContext,
  useState,
  type ReactNode,
} from "react";
import {
  QueryCache,
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { api, ApiError, browserSessionStore } from "./api/client";
import { dismissNotice, notify } from "./notices";
import type { Me, Model, Overview } from "./api/types";
import {
  insideLauncher,
  listenForLauncherEvents,
  listenForLauncherSession,
  renewFromLauncher,
  requestLauncherSession,
  tellLauncherLogout,
} from "./launcher";

export const queries = new QueryClient({
  // A lost connection is said once at the top and retired as soon as a read
  // succeeds again; each screen still shows its own detail.
  queryCache: new QueryCache({
    onError: (error) => {
      if (
        error instanceof ApiError &&
        (error.status === 0 || error.status >= 500) &&
        error.code !== "SESSION_RENEWAL_PENDING"
      )
        notify(
          error.code === "READ_TIMEOUT"
            ? "PokeApp está tardando en responder. Lo reintentamos solo."
            : "No se pudo conectar con PokeApp. Lo reintentamos solo; no hace falta recargar.",
          "warn",
          { key: "connectivity", ttl: 30000 },
        );
    },
    onSuccess: () => dismissNotice("connectivity"),
  }),
  defaultOptions: {
    queries: {
      staleTime: 15000,
      // A dropped connection or a 5xx right after a confirmed change must not
      // leave the old figures on screen: retried at 1, 2 and 4 s.
      retry: (count, error) =>
        count < 3 &&
        error instanceof ApiError &&
        (error.status === 0 || error.status >= 500) &&
        error.code !== "SESSION_RENEWAL_PENDING",
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
      // Coming back to the window shows what changed meanwhile (stale reads
      // only: at most one refetch per screen, never a polling loop).
      refetchOnWindowFocus: true,
      // What others change (results, their deaths, an administrator) reaches
      // the screen being looked at within a minute; hidden windows pause.
      refetchInterval: 60000,
      refetchIntervalInBackground: false,
    },
    mutations: { retry: false },
  },
});
// Every screen the trainer is looking at reads again (inactive ones refetch
// when opened): after a confirmed save sync, another active save, items.
export function refreshEverything() {
  return queries.invalidateQueries();
}
// One sync can announce several confirmed steps within a moment (each copy
// accepted, then the end of the sync). Each refresh cancels the reads in
// flight, so close events become one refresh.
let refreshTimer: ReturnType<typeof setTimeout> | undefined;
export function refreshSoon(delay = 400) {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => void refreshEverything(), delay);
}
const sessionLost = (error: unknown) =>
  error instanceof ApiError && (error.status === 401 || error.status === 403);
const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
type State = {
  me: Me | null;
  setMe: (me: Me | null) => void;
  // A remembered session is being renewed: no sign-in form in the meantime.
  restoring: boolean;
  season: string;
  setSeason: (id: string) => void;
  logout: () => void;
  adminOperationPending: boolean;
  holdAdminNavigation: () => () => void;
  accountsEnabled: boolean;
  // False until the server (or the last visit) has said which options exist.
  capabilitiesKnown: boolean;
  registrationEnabled: boolean;
  bootstrapRequired: boolean;
  renewalEnabled: boolean;
};
const Context = createContext<State | null>(null);
type Capabilities = {
  enabled: boolean;
  registration_enabled: boolean;
  bootstrap_required: boolean;
  renewal_enabled: boolean;
};
export function AppState({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [season, setSeason] = useState("");
  // Nothing about the sign-in options is stored in the browser: until the
  // server answers, the sign-in screen holds their place instead.
  const [capabilitiesKnown, setCapabilitiesKnown] = useState(false);
  const [accountsEnabled, setAccountsEnabled] = useState(false);
  const [registrationEnabled, setRegistrationEnabled] = useState(false);
  const [bootstrapRequired, setBootstrapRequired] = useState(false);
  const [renewalEnabled, setRenewalEnabled] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void api
      .request<Capabilities>(
        "/v1/auth/account-capabilities",
        { signal: controller.signal },
        false,
      )
      .then((value) => {
        setAccountsEnabled(value.enabled === true);
        setRegistrationEnabled(value.registration_enabled === true);
        setBootstrapRequired(value.bootstrap_required === true);
        setRenewalEnabled(value.renewal_enabled === true);
        setCapabilitiesKnown(true);
      })
      .catch(() => setCapabilitiesKnown(true));
    return () => controller.abort();
  }, []);
  const [restoring, setRestoring] = useState(
    () => !insideLauncher() && browserSessionStore.read() !== null,
  );
  // In a browser: the sign-in survives reloads and restarts until the trainer
  // signs out or the session is really rejected (never on a slow network).
  useEffect(() => {
    if (insideLauncher()) return;
    api.persist = browserSessionStore;
    let cancelled = false;
    void (async () => {
      for (let attempt = 0; attempt < 6 && !cancelled; attempt++) {
        try {
          if (!(await api.restore()) && !api.signedIn) break;
          const value = await api.request<Me>("/v1/me");
          if (!cancelled) setMe(value);
          break;
        } catch (error) {
          if (sessionLost(error) || !api.signedIn) break;
          await pause(Math.min(8000, 1000 * 2 ** attempt));
        }
      }
      if (!cancelled) setRestoring(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  // Inside PokeApp Launcher: one sign-in. The Launcher keeps the session
  // (encrypted on this PC) and hands this web an access token, kept in memory
  // only; an explicit sign-out here also signs the Launcher out.
  useEffect(() => {
    if (!insideLauncher()) return;
    api.renewSession = renewFromLauncher;
    let adopting = 0;
    const stop = listenForLauncherSession(
      (session, trainerId) => {
        if (api.signedIn) return api.renewAccess(session);
        api.setSession(session);
        const turn = ++adopting;
        void (async () => {
          // A slow or failed /me is retried; only a rejected session drops it.
          for (let attempt = 0; attempt < 6 && turn === adopting; attempt++) {
            try {
              const value = await api.request<Me>("/v1/me");
              if (value.trainer_id === trainerId) setMe(value);
              else api.setSession(null);
              return;
            } catch (error) {
              if (sessionLost(error)) return api.setSession(null);
              await pause(Math.min(8000, 1000 * 2 ** attempt));
            }
          }
        })();
      },
      // The Launcher has no session any more: a token it handed out cannot be
      // renewed, so the web signs out too. A web that signed in on its own
      // (it holds its own refresh token) is left alone.
      () => {
        if (api.signedIn && api.launcherSession) api.logout();
      },
    );
    const events = listenForLauncherEvents(() => refreshSoon());
    requestLauncherSession();
    return () => {
      stop();
      events();
      api.renewSession = null;
    };
  }, []);
  const [adminHolds, setAdminHolds] = useState(0);
  const holdAdminNavigation = useCallback(() => {
    setAdminHolds((count) => count + 1);
    return () => setAdminHolds((count) => Math.max(0, count - 1));
  }, []);
  api.onExpired = () => {
    void queries.cancelQueries();
    queries.clear();
    setMe(null);
    setSeason("");
    setAdminHolds(0);
  };
  return (
    <QueryClientProvider client={queries}>
      <Context
        value={{
          me,
          setMe,
          restoring: restoring && !me,
          season,
          setSeason,
          logout: () => {
            tellLauncherLogout();
            api.logout();
          },
          adminOperationPending: adminHolds > 0,
          holdAdminNavigation,
          accountsEnabled,
          capabilitiesKnown,
          registrationEnabled,
          bootstrapRequired,
          renewalEnabled,
        }}
      >
        {children}
      </Context>
    </QueryClientProvider>
  );
}
export function useApp() {
  const value = useContext(Context);
  if (!value) throw new Error("Missing app context");
  return value;
}
export function useViewer() {
  return useContext(Context)?.me?.trainer_id;
}
// `live` polls while the screen is open (admin consoles), so a change made
// elsewhere appears without reloading; commands still invalidate at once.
export function useRead<T>(path: string, enabled = true, live?: number) {
  const { me } = useApp();
  return useQuery({
    queryKey: [me?.trainer_id, path],
    queryFn: ({ signal }) => api.request<T>(path, { signal }),
    enabled: Boolean(me) && enabled,
    ...(live ? { refetchInterval: live } : {}),
  });
}
export function useOverview() {
  const { season } = useApp();
  return useRead<Overview>(
    `/v1/read/seasons/${season}/overview`,
    Boolean(season),
  );
}
// «Mi PC» shows the trainer's ACTIVE save: the one their Launcher has
// selected and synced (personal record) — the same game on every screen.
// When the selected season competes with that same game, its copy is shown
// instead (identical file, plus competitive marks such as deaths). A season
// bound to another game is named, never silently swapped in. Refreshed while
// on screen, so a save made in game appears after the Launcher syncs it.
export function useMyPC(enabled = true) {
  const { season } = useApp();
  const seasonPc = useRead<Model<"PCRead">>(
    `/v1/read/seasons/${season}/pc`,
    Boolean(season) && enabled,
    15000,
  );
  const personal = useRead<Model<"PCRead">>("/v1/me/pc", enabled, 15000);
  const active = personal.data?.status === "ready" ? personal.data : null;
  const competing = seasonPc.data?.status === "ready" ? seasonPc.data : null;
  const sameGame =
    !!active && !!competing && active.save?.game === competing.save?.game;
  const data = sameGame || !active ? (competing ?? personal.data) : active;
  return {
    data,
    error: data ? null : personal.error,
    isPending: (Boolean(season) && seasonPc.isPending) || personal.isPending,
    personal: data !== competing,
    // The season competes with another game than the active save.
    seasonGame:
      active && competing && !sameGame ? (competing.save?.game ?? null) : null,
  };
}
export function usePC() {
  const { season } = useApp();
  return useRead<Model<"PCRead">>(
    `/v1/read/seasons/${season}/pc`,
    Boolean(season),
  );
}
