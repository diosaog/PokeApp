import { useEffect, useState } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
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
} from "lucide-react";
import { api } from "./api/client";
import type { Model } from "./api/types";
import { useApp, useRead } from "./state";
import { Field, Notice, Submit, form, text } from "./ui";
import {
  HomePage,
  LeaguePage,
  TrainersPage,
  PCPage,
  SavesPage,
  ShopPage,
  HallPage,
} from "./features/core";
import { CupsPage } from "./features/cups";
import { TrialsPage } from "./features/trials";
import { AdminPage } from "./features/admin";
import { BattlePage } from "./features/team-preview";

const links = [
  ["/", "Inicio", Home],
  ["/liga", "Liga", Trophy],
  ["/battle", "Batallas", Swords],
  ["/entrenadores", "Entrenadores", Users],
  ["/pc", "Mi PC", Box],
  ["/tienda", "Tienda", ShoppingBag],
  ["/copa", "Copa", Crown],
  ["/hall", "Hall de la Fama", Trophy],
  ["/juicios", "Juicios", Scale],
  ["/saves", "Saves y Launcher", HardDrive],
] as const;
function Login() {
  const { setMe } = useApp(),
    [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null);
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
            La próxima
            <br />
            victoria
            <br />
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
        <ShieldCheck size={32} />
        <h2>Bienvenido, entrenador.</h2>
        <p>Entra con tu identidad y PIN de PokeApp.</p>
        <form
          onSubmit={async (event) => {
            const data = form(event);
            if (pending) return;
            setPending(true);
            setError(null);
            try {
              setMe(await api.login(text(data, "trainer"), text(data, "pin")));
            } catch (err) {
              setError(err);
            } finally {
              setPending(false);
            }
          }}
        >
          <Field label="Entrenador">
            <input name="trainer" autoComplete="username" required autoFocus />
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
          <Submit pending={pending || !api.configured}>Entrar a PokeApp</Submit>
        </form>
        <p className="caption">
          Tu PIN y tu sesión no se guardan en este navegador.
        </p>
      </section>
    </main>
  );
}
function SeasonPicker() {
  const { season, setSeason } = useApp(),
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
          value={result.data?.items.some((s) => s.id === season) ? season : ""}
          onChange={(e) => setSeason(e.target.value)}
        >
          <option value="" disabled>
            {result.isPending ? "Cargando temporadas…" : "Selecciona temporada"}
          </option>
          {result.data?.items.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} · {s.status}
            </option>
          ))}
        </select>
      </label>
      {offset > 0 && (
        <button
          onClick={() => setOffset(Math.max(0, offset - 50))}
          aria-label="Temporadas anteriores"
        >
          ←
        </button>
      )}
      {result.data?.next_offset != null && (
        <button
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
  const { me, logout } = useApp(),
    [menu, setMenu] = useState(false),
    location = useLocation();
  useEffect(() => {
    setMenu(false);
    window.scrollTo(0, 0);
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [location.pathname]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenu(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  if (!me) return <Login />;
  return (
    <div
      className={`app-shell section-${location.pathname.split("/")[1] || "home"}`}
    >
      <a className="skip" href="#main">
        Saltar al contenido
      </a>
      <aside className={menu ? "sidebar expanded" : "sidebar"}>
        <Link to="/" className="brand">
          <i className="pokeball" />
          POKE<span>APP</span>
        </Link>
        <p className="nav-label">CENTRO DE COMPETICIÓN</p>
        <nav aria-label="Principal">
          {links.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              <Icon size={19} />
              {label}
              <ArrowUpRight className="nav-arrow" size={14} />
            </NavLink>
          ))}
          {me.is_admin && (
            <NavLink to="/admin">
              <Settings2 size={19} />
              Administración
            </NavLink>
          )}
        </nav>
        <div className="profile">
          <div className="avatar">
            {me.display_name.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <strong>{me.display_name}</strong>
            <span>{me.is_admin ? "Administrador" : "Entrenador"}</span>
          </div>
          <button
            aria-label="Cerrar sesión"
            className="icon-button"
            onClick={logout}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="workspace">
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
          {!me.globally_enabled ? (
            <section className="empty">
              Tu entrenador está deshabilitado. Contacta con la administración.
            </section>
          ) : (
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/liga" element={<LeaguePage />} />
              <Route path="/battle" element={<BattlePage />} />
              <Route path="/entrenadores" element={<TrainersPage />} />
              <Route path="/pc" element={<PCPage />} />
              <Route path="/tienda" element={<ShopPage />} />
              <Route path="/copa/*" element={<CupsPage />} />
              <Route path="/hall" element={<HallPage />} />
              <Route path="/juicios" element={<TrialsPage />} />
              <Route
                path="/admin"
                element={
                  me.is_admin ? <AdminPage /> : <Navigate to="/" replace />
                }
              />
              <Route path="/saves" element={<SavesPage />} />
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
          )}
        </main>
        <footer>
          POKEAPP <span>Tu próxima historia está por jugar.</span>
        </footer>
      </div>
    </div>
  );
}
