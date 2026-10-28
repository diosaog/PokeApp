import { useEffect, useRef, useState, lazy, Suspense } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  Home,
  Swords,
  Trophy,
  Users,
  Box,
  ShoppingBag,
  Crown,
  Scale,
  Settings2,
  HardDrive,
  LogOut,
  Menu,
  ArrowUpRight,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "./api/client";
import type { Model } from "./api/types";
import { useApp, useRead } from "./state";
import { Field, Notice, Submit, Loading, form, text } from "./ui";
// Every screen behind the sign-in loads on demand: the sign-in screen ships
// only the shell. Once signed in, the screens are fetched while the browser is
// idle (warmScreens), so moving between them stays instant.
const screens = {
  core: () => import("./features/core"),
  cups: () => import("./features/cups"),
  trials: () => import("./features/trials"),
  battle: () => import("./features/team-preview"),
  scouting: () => import("./features/scouting"),
  profile: () => import("./features/trainer-profile"),
  desktop: () => import("./features/desktop"),
  saves: () => import("./features/saves"),
};
const HomePage = lazy(() =>
  screens.core().then((m) => ({ default: m.HomePage })),
);
const LeaguePage = lazy(() =>
  screens.core().then((m) => ({ default: m.LeaguePage })),
);
const TrainersPage = lazy(() =>
  screens.core().then((m) => ({ default: m.TrainersPage })),
);
const PCPage = lazy(() => screens.core().then((m) => ({ default: m.PCPage })));
const ShopPage = lazy(() =>
  screens.core().then((m) => ({ default: m.ShopPage })),
);
const HallPage = lazy(() =>
  screens.core().then((m) => ({ default: m.HallPage })),
);
const CupsPage = lazy(() =>
  screens.cups().then((m) => ({ default: m.CupsPage })),
);
const TrialsPage = lazy(() =>
  screens.trials().then((m) => ({ default: m.TrialsPage })),
);
function warmScreens() {
  const idle =
    window.requestIdleCallback ??
    ((run: () => void) => window.setTimeout(run, 200));
  idle(() => {
    for (const load of Object.values(screens)) void load().catch(() => {});
  });
}
const AdminPage = lazy(() =>
  import("./features/admin").then((m) => ({ default: m.AdminPage })),
);
import { seasonLabel } from "./features/admin-labels";
const BattlePage = lazy(() =>
  screens.battle().then((m) => ({ default: m.BattlePage })),
);
const ScoutingPage = lazy(() =>
  screens.scouting().then((m) => ({ default: m.ScoutingPage })),
);
const TrainerProfilePage = lazy(() =>
  screens.profile().then((m) => ({ default: m.TrainerProfilePage })),
);
const DesktopPage = lazy(() =>
  screens.desktop().then((m) => ({ default: m.DesktopPage })),
);
const SavesPage = lazy(() =>
  screens.saves().then((m) => ({ default: m.SavesPage })),
);
import { insideLauncher } from "./launcher";
import { RegistrationForm } from "./features/registration";
import { PinForm, pinRecoveryKey } from "./features/account-editor";
import { play } from "./sound";
import { SoundToggle } from "./features/preferences";
const AdminAccountsPage = lazy(() =>
  import("./features/admin-accounts").then((m) => ({
    default: m.AdminAccountsPage,
  })),
);

const linkGroups = [
  { label: "GENERAL", links: [["/", "Inicio", Home]] },
  {
    label: "COMPETICIÓN",
    links: [
      ["/liga", "Liga", Trophy],
      ["/battle", "Batallas", Swords],
      ["/copa", "Copa", Crown],
    ],
  },
  {
    label: "COLECCIÓN",
    links: [
      ["/entrenadores", "Entrenadores", Users],
      ["/pc", "Mi PC", Box],
    ],
  },
  { label: "ECONOMÍA", links: [["/tienda", "Tienda", ShoppingBag]] },
  {
    label: "HISTORIAL",
    links: [
      ["/hall", "Hall de la Fama", Trophy],
      ["/juicios", "Juicios", Scale],
      ["/saves", "Saves y Launcher", HardDrive],
    ],
  },
] as const;
function Login() {
  const {
      setMe,
      accountsEnabled,
      capabilitiesKnown,
      registrationEnabled,
      renewalEnabled,
      bootstrapRequired,
    } = useApp(),
    [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null),
    [register, setRegister] = useState(false),
    [renew, setRenew] = useState(false),
    [created, setCreated] = useState(""),
    location = useLocation(),
    navigate = useNavigate();
  // Signed out on a desktop tool: leave its route so PokeApp Launcher closes
  // the native panel instead of keeping it over the sign-in screen.
  useEffect(() => {
    if (insideLauncher() && location.pathname.startsWith("/escritorio/"))
      navigate("/", { replace: true });
  }, [location.pathname, navigate]);
  return (
    <main className="login">
      <section className="login-story">
        <Link to="/" className="brand">
          <i className="pokeball" />
          POKE<span>APP</span>
        </Link>
        <div>
          <p className="eyebrow">TU EQUIPO. TU LIGA. TU HISTORIA.</p>
          <h1>
            La próxima <br />
            victoria <br />
            <em>empieza aquí.</em>
          </h1>
          <p>
            Prepara tu equipo. Defiende tu división.
            <br />
            Deja tu nombre en el Hall de la Fama.
          </p>
        </div>
        <p className="caption">POKEAPP 2.0 · COMPETICIÓN ENTRE AMIGOS</p>
        <div className="orbit" aria-hidden="true" />
      </section>
      <section className="login-form">
        {register && registrationEnabled ? (
          <RegistrationForm
            bootstrapRequired={bootstrapRequired}
            onCancel={() => setRegister(false)}
            onRegistered={(name) => {
              setCreated(name);
              setRegister(false);
            }}
          />
        ) : (
          <>
            <ShieldCheck size={32} />
            <h2>Bienvenido, entrenador.</h2>
            <p>Entra con tu identidad y PIN de PokeApp.</p>
            {created && (
              <p role="status">
                Cuenta creada. Ya puedes entrar con tu nombre y PIN.
              </p>
            )}
            <form
              onSubmit={async (event) => {
                const data = form(event);
                if (pending) return;
                setPending(true);
                setError(null);
                try {
                  setMe(
                    await api.login(text(data, "trainer"), text(data, "pin")),
                  );
                } catch (err) {
                  setError(err);
                } finally {
                  setPending(false);
                }
              }}
            >
              <Field label="Entrenador">
                <input
                  key={created}
                  defaultValue={created}
                  name="trainer"
                  autoComplete="username"
                  required
                  autoFocus
                />
              </Field>
              <Field label="PIN">
                <input
                  name="pin"
                  type="password"
                  inputMode="numeric"
                  autoComplete="current-password"
                  required
                  maxLength={128}
                />
              </Field>
              <Notice error={error} />
              {!api.configured && (
                <p role="alert">
                  El servidor todavía no está configurado para este despliegue.
                </p>
              )}
              <Submit pending={pending || !api.configured}>
                Entrar a PokeApp
              </Submit>
            </form>
            <p className="caption">
              Tu PIN y tu sesión no se guardan en este navegador.
            </p>
            {!capabilitiesKnown && (
              // Holds the place of the registration and PIN renewal offers
              // until the server answers, so the form does not jump.
              <div className="login-reserve" aria-hidden="true">
                <p>¿Todavía no tienes cuenta?</p>
                <button tabIndex={-1} disabled>
                  Crear cuenta
                </button>
                <button tabIndex={-1} disabled>
                  Renovar PIN con autorización
                </button>
              </div>
            )}
            {registrationEnabled && (
              <>
                <p>¿Todavía no tienes cuenta?</p>
                <button disabled={pending} onClick={() => setRegister(true)}>
                  Crear cuenta
                </button>
              </>
            )}
            {renewalEnabled && (
              <>
                <button disabled={pending} onClick={() => setRenew(!renew)}>
                  Renovar PIN con autorización
                </button>
                {renew && <PinForm renewal />}
              </>
            )}
            {accountsEnabled && sessionStorage.getItem(pinRecoveryKey) && (
              <PinForm recovery />
            )}
          </>
        )}
      </section>
    </main>
  );
}
function SeasonPicker() {
  const { season, setSeason, adminOperationPending } = useApp(),
    [offset, setOffset] = useState(0);
  const result = useRead<Model<"SeasonPage">>(
    `/v1/read/seasons?offset=${offset}`,
  );
  useEffect(() => {
    if (!season && result.data?.items.length)
      setSeason(
        (
          result.data.items.find((s) => s.status === "active") ||
          result.data.items[0]
        ).id,
      );
  }, [result.data, season, setSeason]);
  return (
    <div className="season-picker">
      <label>
        <span className="sr-only">Temporada</span>
        <select
          disabled={adminOperationPending}
          value={result.data?.items.some((s) => s.id === season) ? season : ""}
          onChange={(e) => setSeason(e.target.value)}
        >
          <option value="" disabled>
            {result.isPending ? "Cargando temporadas…" : "Selecciona temporada"}
          </option>
          {result.data?.items.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} · {seasonLabel(s.status)}
            </option>
          ))}
        </select>
      </label>
      {offset > 0 && (
        <button
          disabled={adminOperationPending}
          onClick={() => setOffset(Math.max(0, offset - 50))}
          aria-label="Temporadas anteriores"
        >
          ←
        </button>
      )}
      {result.data?.next_offset != null && (
        <button
          disabled={adminOperationPending}
          onClick={() => setOffset(result.data!.next_offset!)}
          aria-label="Más temporadas"
        >
          →
        </button>
      )}
      <Notice error={result.error} />
    </div>
  );
}
export default function App() {
  const { me, logout, adminOperationPending, accountsEnabled } = useApp(),
    [menu, setMenu] = useState(false),
    location = useLocation(),
    visited = useRef(location.pathname);
  const signedIn = Boolean(me);
  useEffect(() => {
    if (signedIn) warmScreens();
  }, [signedIn]);
  useEffect(() => {
    setMenu(false);
    window.scrollTo(0, 0);
    document.getElementById("main")?.focus({ preventScroll: true });
    // A soft cue when the trainer moves to another screen (not on first load).
    if (visited.current !== location.pathname) play("nav");
    visited.current = location.pathname;
  }, [location.pathname]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenu(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  useEffect(() => {
    if (!adminOperationPending) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [adminOperationPending]);
  if (!me) return <Login />;
  return (
    <div
      className={`app-shell section-${location.pathname.split("/")[1] || "home"}`}
      // Presentation only: Entrenadores holds three screens with their own scene.
      data-view={
        location.pathname.startsWith("/entrenadores/")
          ? location.pathname === "/entrenadores/scouting"
            ? "scouting"
            : "profile"
          : undefined
      }
    >
      <a className="skip" href="#main">
        Saltar al contenido
      </a>
      <aside className={menu ? "sidebar expanded" : "sidebar"}>
        <Link
          to="/"
          className="brand"
          aria-disabled={adminOperationPending || undefined}
          onClick={(event) => {
            if (adminOperationPending) event.preventDefault();
            else setMenu(false);
          }}
        >
          <i className="pokeball" />
          POKE<span>APP</span>
        </Link>
        <button
          className="mobile-close icon-button"
          aria-label="Cerrar navegación"
          onClick={() => setMenu(false)}
        >
          <X />
        </button>
        <p className="nav-label">CENTRO DE COMPETICIÓN</p>
        <nav aria-label="Principal">
          {linkGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.links.map(([to, label, Icon]) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  aria-disabled={adminOperationPending || undefined}
                  onClick={(event) => {
                    if (adminOperationPending) event.preventDefault();
                    else setMenu(false);
                  }}
                >
                  <Icon size={19} />
                  {label}
                  <ArrowUpRight className="nav-arrow" size={14} />
                </NavLink>
              ))}
            </div>
          ))}
          {me.is_admin && (
            <div className="nav-group">
              <span className="nav-group-label">ADMIN</span>
              <NavLink
                to="/admin"
                end
                aria-disabled={adminOperationPending || undefined}
                onClick={(event) => {
                  if (adminOperationPending) event.preventDefault();
                  else setMenu(false);
                }}
              >
                <Settings2 size={19} />
                Administración
              </NavLink>
              {accountsEnabled && (
                <NavLink
                  to="/admin/cuentas"
                  aria-disabled={adminOperationPending}
                  onClick={(e) => {
                    if (adminOperationPending) e.preventDefault();
                    else setMenu(false);
                  }}
                >
                  <Users size={19} />
                  Cuentas
                </NavLink>
              )}
            </div>
          )}
        </nav>
        <div className="profile">
          <div className="avatar">
            {me.display_name.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <strong>{me.display_name}</strong>
            <span>{me.is_admin ? "Administrador" : "Entrenador"}</span>
            {accountsEnabled && (
              <Link
                to={`/entrenadores/${me.trainer_id}`}
                onClick={(e) => {
                  if (adminOperationPending) e.preventDefault();
                  else setMenu(false);
                }}
              >
                Mi perfil
              </Link>
            )}
          </div>
          <SoundToggle />
          <button
            aria-label="Cerrar sesión"
            className="icon-button"
            disabled={adminOperationPending}
            onClick={logout}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        {/* Decorative light of the current area; a new node per area keeps
            route changes free of layout shift. */}
        <div
          className="scene-fx"
          key={location.pathname.split("/")[1] || "home"}
          aria-hidden="true"
        />
        <header className="topbar">
          <button
            className="mobile-menu icon-button"
            aria-expanded={menu}
            aria-label="Abrir navegación"
            onClick={() => setMenu(!menu)}
          >
            <Menu />
          </button>
          <span className="topbar-caption">CADA JORNADA CUENTA</span>
          <SeasonPicker />
          <span className="connection">
            <i />
            PokeApp V2
          </span>
        </header>
        <main id="main" tabIndex={-1}>
          {adminOperationPending && (
            <p role="status" className="notice">
              Confirma el resultado de la operación pendiente antes de cambiar
              de pantalla, temporada o cerrar sesión.
            </p>
          )}
          {!me.globally_enabled ? (
            <section className="empty">
              Tu entrenador está deshabilitado. Contacta con la administración.
            </section>
          ) : (
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/liga" element={<LeaguePage />} />
                <Route path="/battle" element={<BattlePage />} />
                <Route path="/entrenadores" element={<TrainersPage />} />
                <Route
                  path="/entrenadores/scouting"
                  element={<ScoutingPage />}
                />
                <Route
                  path="/entrenadores/:trainerId"
                  element={<TrainerProfilePage />}
                />
                <Route path="/pc" element={<PCPage />} />
                <Route path="/tienda" element={<ShopPage />} />
                <Route path="/copa/*" element={<CupsPage />} />
                <Route path="/hall" element={<HallPage />} />
                <Route path="/juicios" element={<TrialsPage />} />
                <Route
                  path="/admin"
                  element={
                    me.is_admin ? (
                      <Suspense fallback={<Loading />}>
                        <AdminPage />
                      </Suspense>
                    ) : (
                      <Navigate to="/" replace />
                    )
                  }
                />
                <Route path="/saves" element={<SavesPage />} />
                <Route path="/escritorio/:panel/*" element={<DesktopPage />} />
                <Route
                  path="/admin/cuentas"
                  element={
                    me.is_admin && accountsEnabled ? (
                      <Suspense fallback={<Loading />}>
                        <AdminAccountsPage />
                      </Suspense>
                    ) : (
                      <Navigate to="/" replace />
                    )
                  }
                />
                <Route
                  path="*"
                  element={
                    <section className="empty">
                      <h1>Página no encontrada</h1>
                      <Link to="/">Volver a Inicio</Link>
                    </section>
                  }
                />
              </Routes>
            </Suspense>
          )}
        </main>
        <footer>
          POKEAPP <span>Tu próxima historia está por jugar.</span>
        </footer>
      </div>
    </div>
  );
}
