import {
  createContext,
  useCallback,
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
};
const Context = createContext<State | null>(null);
export function AppState({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [season, setSeason] = useState("");
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
          logout: () => api.logout(),
          adminOperationPending: adminHolds > 0,
          holdAdminNavigation,
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
export function useRead<T>(path: string, enabled = true) {
  const { me } = useApp();
  return useQuery({
    queryKey: [me?.trainer_id, path],
    queryFn: ({ signal }) => api.request<T>(path, { signal }),
    enabled: Boolean(me) && enabled,
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
