import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import { Empty, Heading, Loading, Notice, Tag } from "../ui";
import { TrainerPhoto, StatPill } from "../pokemon/presentation";
import { GameProgress } from "./progress";
import { participantLabel } from "./admin-labels";
import { WithSeason } from "./core";
import { useState } from "react";
import type { AccountProfile } from "./account-editor";

export function TrainersPage() {
  const { accountsEnabled } = useApp();
  return accountsEnabled ? <AccountTrainers /> : <SeasonTrainers />;
}
function AccountTrainers() {
  const { me, season } = useApp(),
    overview = useOverview(),
    [offset, setOffset] = useState(0);
  const accounts = useRead<{ items: AccountProfile[]; has_more: boolean }>(
    `/v1/accounts?offset=${offset}`,
  );
  const league = useRead<Model<"LeagueGeneralRead">>(
    `/v1/read/seasons/${season}/league`,
    !!season,
  );
  return (
    <>
      <Heading eyebrow="LA COMUNIDAD" title="Entrenadores">
        Cada equipo tiene una historia. Conoce a tus rivales.
      </Heading>
      <Notice error={accounts.error} />
      {accounts.isPending ? (
        <Loading />
      ) : (
        <div className="trainers-roster">
          {accounts.data?.items.map((a) => {
            const p = overview.data?.players.find(
                (p) => p.trainer_id === a.trainer_id,
              ),
              row = league.data?.rows.find(
                (r) => r.trainer_id === a.trainer_id,
              );
            return (
              <article className="card trainer-card" key={a.trainer_id}>
                <div className="trainer-card-top">
                  <TrainerPhoto name={a.display_name} url={a.photo_url} />
                  <div className="trainer-summary">
                    <h2>{a.display_name}</h2>
                    {a.trainer_id === me?.trainer_id && <Tag>TÚ</Tag>}
                    {p ? (
                      <div className="mini-stats">
                        <StatPill label="Puntos" value={row?.total_points} />
                        <StatPill label="Monedas" value={row?.coin_balance} />
                        <StatPill
                          label="Muertos"
                          value={row?.dead_count ?? "—"}
                        />
                      </div>
                    ) : (
                      <p>Sin participación en esta temporada</p>
                    )}
                  </div>
                </div>
                {p && (
                  <div className="trainer-badges">
                    <GameProgress progress={p.progress} compact />
                  </div>
                )}
                <Link
                  className="button primary"
                  to={`/entrenadores/${a.trainer_id}`}
                >
                  Ver perfil <ArrowUpRight size={16} />
                </Link>
              </article>
            );
          })}
        </div>
      )}
      <div className="section-row">
        <button disabled={offset === 0} onClick={() => setOffset(offset - 50)}>
          Anteriores
        </button>
        <button
          disabled={!accounts.data?.has_more}
          onClick={() => setOffset(offset + 50)}
        >
          Siguientes
        </button>
      </div>
    </>
  );
}
function SeasonTrainers() {
  const { season, me } = useApp(),
    overview = useOverview();
  const league = useRead<Model<"LeagueGeneralRead">>(
    `/v1/read/seasons/${season}/league`,
    !!season,
  );
  return (
    <>
      <Heading eyebrow="LA COMUNIDAD" title="Entrenadores">
        Cada equipo tiene una historia. Conoce a tus rivales.
      </Heading>
      <WithSeason>
        <Notice error={overview.error || league.error} />
        {overview.isPending ? (
          <Loading />
        ) : (
          <div className="trainers-roster">
            {[...(overview.data?.players ?? [])]
              .sort((a, b) =>
                a.display_name.localeCompare(b.display_name, "es", {
                  sensitivity: "base",
                }),
              )
              .map((p) => {
                const row = league.data?.rows.find(
                  (r) => r.trainer_id === p.trainer_id,
                );
                return (
                  <article
                    className={`card trainer-card ${p.status !== "active" ? "inactive-trainer" : ""}`}
                    key={p.id}
                  >
                    <div className="trainer-card-top">
                      <TrainerPhoto name={p.display_name} />
                      <div className="trainer-summary">
                        <div className="section-row">
                          <h2>{p.display_name}</h2>
                          {p.trainer_id === me?.trainer_id && <Tag>TÚ</Tag>}
                        </div>
                        {p.status !== "active" && (
                          <small>{participantLabel(p.status)}</small>
                        )}
                        <div className="mini-stats">
                          <StatPill label="Puntos" value={row?.total_points} />
                          <StatPill label="Monedas" value={row?.coin_balance} />
                          <StatPill
                            label="Muertos"
                            value={row?.dead_count ?? "—"}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="trainer-badges">
                      <GameProgress progress={p.progress} compact />
                    </div>
                    <Link
                      className="button primary"
                      to={`/entrenadores/${p.trainer_id}`}
                    >
                      Ver Equipo y Cajas <ArrowUpRight size={16} />
                    </Link>
                  </article>
                );
              })}
          </div>
        )}
        {overview.data?.players.length === 0 && (
          <Empty>Aún no hay entrenadores en esta temporada.</Empty>
        )}
      </WithSeason>
    </>
  );
}
