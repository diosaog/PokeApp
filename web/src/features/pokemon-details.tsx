import type { Model } from "../api/types";
type Public = Pick<
  Model<"PokemonRead">,
  "species" | "nickname" | "level" | "types" | "item"
> & { moves?: { name: string }[] | null };
export type DetailPokemon =
  | { visibility: "public"; pokemon: Public }
  | { visibility: "self"; pokemon: Model<"PrivatePokemonRead"> };
export function PokemonDetails(props: DetailPokemon) {
  const p = props.pokemon;
  return (
    <>
      <dl className="details">
        <dt>Especie</dt>
        <dd>{p.species}</dd>
        <dt>Nivel</dt>
        <dd>{p.level ?? "—"}</dd>
        <dt>Tipos</dt>
        <dd>{p.types?.join(" / ") || "—"}</dd>
        <dt>Objeto</dt>
        <dd>{p.item || "—"}</dd>
      </dl>
      <h3>Movimientos</h3>
      <div className="moves">
        {p.moves?.length
          ? p.moves.map((m, i) => <span key={i}>{m.name}</span>)
          : "No disponibles."}
      </div>
      {props.visibility === "self" && (
        <>
          <dl className="details">
            <dt>Habilidad</dt>
            <dd>{props.pokemon.ability || "—"}</dd>
            <dt>Naturaleza</dt>
            <dd>{props.pokemon.nature || "—"}</dd>
          </dl>
          {(["ivs", "evs"] as const).map((k) => (
            <div key={k}>
              <h3>{k.toUpperCase()}</h3>
              {props.pokemon[k] ? (
                <dl className="stats-list">
                  {Object.entries(props.pokemon[k]!).map(([stat, v]) => (
                    <div key={stat}>
                      <dt>{stat}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p>No disponibles.</p>
              )}
            </div>
          ))}
        </>
      )}
    </>
  );
}
