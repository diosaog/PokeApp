import { useState, useEffect } from "react";
import type { Model } from "../api/types";
import { useApp } from "../state";
import { ChampionshipReview } from "./championship";
import { OpenMatchday } from "./league-matchday";

// Liga › General, below the standings: opening the next matchday, and the
// final championship review (076: its own audited workflow and permissions,
// unchanged) once the last matchday is closed. Closing a matchday lives at
// the bottom of that matchday's own tab.
export function LeagueOperations({
  data,
  onShowDay = () => {},
}: {
  data: Model<"LeagueGeneralRead">;
  onShowDay?: (dayId: string) => void;
}) {
  const { me } = useApp(),
    day = data.days.find((d) => d.id === data.season.current_matchday_id);
  const eligible =
    data.season.status === "active" &&
    data.rows.some(
      (p) => p.trainer_id === me?.trainer_id && p.status === "active",
    );
  const [review, setReview] = useState(false);
  useEffect(() => {
    if ((eligible || me?.is_admin) && day?.status === "closed") setReview(true);
  }, [eligible, me?.is_admin, day?.status]);
  return (
    <>
      <OpenMatchday data={data} onShowDay={onShowDay} />
      {review && (
        <ChampionshipReview
          participant={!me?.is_admin}
          seasonName={data.season.name}
        />
      )}
    </>
  );
}
