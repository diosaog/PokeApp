import { useEffect, useRef, useState } from "react";
import type { Model } from "../api/types";
import { useApp, useRead } from "../state";
import {
  Card,
  CommandState,
  Field,
  Loading,
  Notice,
  Submit,
  form,
  number,
  text,
  useCommand,
} from "../ui";

type Setup = Model<"SeasonSetup">;
export function Rules({ setup }: { setup: Setup }) {
  const { season } = useApp();
  const query = useRead<Model<"LiveRulesRead">>(
    `/v1/admin/seasons/${season}/rules`,
    !!season,
  );
  return (
    <>
      <Card>
        <h2>Reglas de recompensas</h2>
        <Notice error={query.error} />
        {query.isPending && <Loading />}
        {query.data && (
          <RewardForm
            key={season}
            rules={query.data}
            unavailable={!!query.error}
          />
        )}
      </Card>
      <Structure key={season} setup={setup} />
      <SeasonName key={`name:${season}`} setup={setup} />
    </>
  );
}

function SeasonName({ setup }: { setup: Setup }) {
  const cmd = useRulesCommand(),
    editable = setup.season.status === "draft";
  return (
    <Card>
      <h2>Nombre de temporada</h2>
      <form
        onSubmit={(event) => {
          const values = form(event);
          if (!editable || cmd.pending || cmd.uncertain) return;
          void cmd.execute(
            `/v1/admin/seasons/${setup.season.id}/name`,
            {
              name: text(values, "name"),
              expected_revision: setup.setup_revision,
            } satisfies Model<"RenameSeasonBody">,
            "PUT",
          );
        }}
      >
        <Field label="Nombre">
          <input
            key={setup.setup_revision}
            name="name"
            required
            maxLength={120}
            defaultValue={setup.season.name}
            disabled={!editable || cmd.pending || cmd.uncertain}
          />
        </Field>
        <Submit pending={!editable || cmd.pending || cmd.uncertain}>
          Guardar nombre
        </Submit>
        {!editable && <p>El nombre se conserva desde el inicio de la Liga.</p>}
        <CommandState command={cmd} />
      </form>
    </Card>
  );
}

function useRulesCommand() {
  const cmd = useCommand(),
    { holdAdminNavigation } = useApp();
  useEffect(() => {
    if ((cmd.pending || cmd.uncertain) && holdAdminNavigation)
      return holdAdminNavigation();
  }, [cmd.pending, cmd.uncertain, holdAdminNavigation]);
  return cmd;
}

function RewardForm({
  rules,
  unavailable,
}: {
  rules: Model<"LiveRulesRead">;
  unavailable: boolean;
}) {
  const cmd = useRulesCommand();
  const submittedRevision = useRef<number | null>(null);
  const [source, setSource] = useState(rules),
    [badge, setBadge] = useState(String(rules.badge_reward_coins)),
    [champion, setChampion] = useState(
      String(rules.game_completion_reward_coins),
    ),
    [error, setError] = useState("");
  const changed =
    source.revision !== rules.revision ||
    source.config_revision !== rules.config_revision;
  const busy = cmd.pending || cmd.uncertain;
  const valid = [badge, champion].every(
    (v) =>
      /^\d+$/.test(v) &&
      Number.isSafeInteger(Number(v)) &&
      Number(v) <= 2147483647,
  );
  useEffect(() => {
    if (
      cmd.success &&
      !cmd.pending &&
      rules.revision === submittedRevision.current
    ) {
      setSource(rules);
      submittedRevision.current = null;
    }
  }, [cmd.success, cmd.pending, rules]);
  return (
    <form
      onSubmit={async (event) => {
        event.preventDefault();
        if (busy || changed || unavailable || !rules.editable) return;
        if (!valid) {
          setError("Introduce monedas enteras, desde cero.");
          return;
        }
        setError("");
        submittedRevision.current = source.revision + 1;
        await cmd.execute(
          `/v1/admin/seasons/${rules.season_id}/rules`,
          {
            expected_revision: source.revision,
            expected_config_revision: source.config_revision,
            badge_reward_coins: Number(badge),
            game_completion_reward_coins: Number(champion),
          } satisfies Model<"LiveRulesBody">,
          "PUT",
        );
      }}
    >
      <fieldset disabled={busy || unavailable || !rules.editable}>
        <div className="form-grid">
          <Field label="Monedas por medalla">
            <input
              required
              type="number"
              min={0}
              max={2147483647}
              step={1}
              value={badge}
              onChange={(e) => setBadge(e.target.value)}
            />
          </Field>
          <Field label="Monedas por vencer al Campeón">
            <input
              required
              type="number"
              min={0}
              max={2147483647}
              step={1}
              value={champion}
              onChange={(e) => setChampion(e.target.value)}
            />
          </Field>
        </div>
        <p>Los cambios se aplican desde ahora. Lo anterior no cambia.</p>
        {changed && (
          <div className="notice" role="alert">
            <span>
              Las reglas cambiaron. Ahora: {rules.badge_reward_coins} por
              medalla y {rules.game_completion_reward_coins} por Campeón.
              Conservamos tu edición.
            </span>
            <button type="button" onClick={() => setSource(rules)}>
              He revisado los cambios
            </button>
          </div>
        )}
        {error && <p role="alert">{error}</p>}
        {rules.editable ? (
          <Submit pending={busy || changed}>Guardar cambios</Submit>
        ) : (
          <p>Esta Liga conserva sus reglas históricas.</p>
        )}
      </fieldset>
      <CommandState command={cmd} />
    </form>
  );
}

function Structure({ setup }: { setup: Setup }) {
  const { season } = useApp(),
    cmd = useRulesCommand();
  const [source, setSource] = useState(setup),
    [error, setError] = useState("");
  const config =
    source.config_versions.find((c) => c.is_current) ??
    source.config_versions[0];
  const editable = setup.season.status === "draft" && !config?.used;
  const stale =
    source.config_revision !== setup.config_revision ||
    source.roster_revision !== setup.roster_revision;
  const busy = cmd.pending || cmd.uncertain;
  return (
    <Card>
      <h2>Formato de la Liga</h2>
      {!editable ? (
        <p>
          Las divisiones y jornadas ya preparadas se conservan para proteger la
          competición.
        </p>
      ) : (
        <form
          key={`${source.config_revision}:${source.roster_revision}`}
          onSubmit={(event) => {
            const data = form(event);
            if (busy || stale) return;
            const scores = text(data, "points").split(",").map(Number),
              coins = text(data, "coins").split(",").map(Number);
            const values = ["total", "a", "b", "movement"].map((k) =>
              number(data, k),
            );
            if (
              ![...scores, ...coins, ...values].every(
                (v) => Number.isSafeInteger(v) && v >= 0 && v <= 2147483647,
              ) ||
              values.slice(0, 3).some((v) => v === 0)
            ) {
              setError("Introduce cantidades enteras válidas.");
              return;
            }
            setError("");
            const positions = (v: number[]) =>
              Object.fromEntries(v.map((n, i) => [String(i + 1), n]));
            const body: Model<"ConfigVersionBody"> = {
              name: "Reglas de la Liga",
              effective_from_matchday: 1,
              total_matchdays: values[0],
              division_sizes: { A: values[1], B: values[2] },
              movement_count: values[3],
              scoring: positions(scores),
              coin_rewards: positions(coins),
              rules: {
                badge_reward_coins: 4,
                game_completion_reward_coins: 12,
                ...config?.rules,
                team_lock_required: data.has("lock"),
                last_b_gets_steal: data.has("steal"),
              },
              expected_config_revision: source.config_revision,
              expected_roster_revision: source.roster_revision,
            };
            void cmd.execute(
              `/v1/admin/seasons/${season}/config-versions${config ? `/${config.id}/replace-unused` : ""}`,
              config
                ? {
                    ...body,
                    reason: "Actualización del formato durante la preparación",
                  }
                : body,
            );
          }}
        >
          <fieldset disabled={busy || stale}>
            <div className="form-grid">
              {(
                [
                  [
                    "total",
                    "Total de jornadas",
                    config?.total_matchdays ?? 1,
                    1,
                  ],
                  [
                    "a",
                    "Participantes en A",
                    config?.division_sizes?.A ??
                      Math.ceil(setup.participants.length / 2),
                    1,
                  ],
                  [
                    "b",
                    "Participantes en B",
                    config?.division_sizes?.B ??
                      Math.floor(setup.participants.length / 2),
                    1,
                  ],
                  [
                    "movement",
                    "Ascensos / descensos",
                    config?.movement_count ?? 0,
                    0,
                  ],
                ] as const
              ).map(([name, label, value, min]) => (
                <Field key={name} label={label}>
                  <input
                    name={name}
                    type="number"
                    min={min}
                    max={2147483647}
                    step={1}
                    required
                    defaultValue={value}
                  />
                </Field>
              ))}
              {(
                [
                  ["points", "Puntos por posición", config?.scoring],
                  ["coins", "Monedas por posición", config?.coin_rewards],
                ] as const
              ).map(([name, label, v]) => (
                <Field key={name} label={label}>
                  <input
                    name={name}
                    required
                    pattern="[0-9]+(,[0-9]+)*"
                    placeholder="10,8,6,4"
                    defaultValue={
                      v &&
                      Object.entries(v)
                        .sort((a, b) => Number(a[0]) - Number(b[0]))
                        .map(([, n]) => n)
                        .join(",")
                    }
                  />
                </Field>
              ))}
            </div>
            <label className="check">
              <input
                type="checkbox"
                name="lock"
                defaultChecked={config?.rules.team_lock_required !== false}
              />
              Avisar si falta Team Lock
            </label>
            <label className="check">
              <input
                type="checkbox"
                name="steal"
                defaultChecked={config?.rules.last_b_gets_steal === true}
              />
              Último de B recibe robo
            </label>
            {error && <p role="alert">{error}</p>}
            <Submit pending={busy || stale}>Guardar formato</Submit>
          </fieldset>
          {stale && (
            <p role="alert">
              La plantilla o el formato cambiaron.{" "}
              <button
                type="button"
                disabled={busy}
                onClick={() => setSource(setup)}
              >
                Revisar formato actual
              </button>
            </p>
          )}
        </form>
      )}
      <CommandState command={cmd} />
    </Card>
  );
}
