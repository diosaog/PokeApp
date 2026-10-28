import {
  createContext,
  useCallback,
  useEffect,
  useContext,
  useState,
  type ReactNode,
} from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { api, ApiError } from "./api/client";
import type { Me, Model, Overview } from "./api/types";
import {
  insideLauncher,
  listenForLauncherSession,
  renewFromLauncher,
  requestLauncherSession,
  tellLauncherLogout,
} from "./launcher";

export const queries = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15000,
      retry: (count, error) =>
        count < 1 && error instanceof ApiError && error.status >= 500,
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
type State = {
  me: Me | null;
  setMe: (me: Me | null) => void;
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
  // Inside PokeApp Launcher: one sign-in. The Launcher keeps the session
  // (encrypted on this PC) and hands this web an access token, kept in memory
  // only; an explicit sign-out here also signs the Launcher out.
  useEffect(() => {
    if (!insideLauncher()) return;
    api.renewSession = renewFromLauncher;
    const stop = listenForLauncherSession((session, trainerId) => {
      if (api.signedIn) return api.renewAccess(session);
      api.setSession(session);
      void api
        .request<Me>("/v1/me")
        .then((value) => {
          if (value.trainer_id === trainerId) setMe(value);
          else api.setSession(null);
        })
        .catch(() => api.setSession(null));
    });
    requestLauncherSession();
    return () => {
      stop();
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
    refetchInterval: live,
  });
}
export function useOverview() {
  const { season } = useApp();
  return useRead<Overview>(
    `/v1/read/seasons/${season}/overview`,
    Boolean(season),
  );
}
export function usePC() {
  const { season } = useApp();
  return useRead<Model<"PCRead">>(
    `/v1/read/seasons/${season}/pc`,
    Boolean(season),
  );
}
