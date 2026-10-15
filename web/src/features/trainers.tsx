import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import type { Model } from "../api/types";
import { useApp, useOverview, useRead } from "../state";
import { Empty, Heading, Loading, Notice, Tag } from "../ui";
import { TrainerPhoto, StatPill } from "../pokemon/presentation";
import { GameProgress } from "./progress";
import { participantLabel } from "./admin-labels";
import { WithSeason } from "./core";

export function TrainersPage() {
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
