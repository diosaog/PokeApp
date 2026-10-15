import type { Model } from "../api/types";
import { pokemonName, pokemonTitle, statName } from "../pokemon/localization";
import {
  ItemIcon,
  MovePopover,
  PokemonSprite,
  TypeBadge,
} from "../pokemon/presentation";
import { Modal } from "../ui";
type Public = Pick<
  Model<"PokemonRead">,
  "species" | "nickname" | "level" | "types" | "item"
> & { moves?: { name: string }[] | null };
export type DetailPokemon =
  | { visibility: "public"; pokemon: Public }
  | { visibility: "self"; pokemon: Model<"PrivatePokemonRead"> };
export function PokemonDetailModal(
  props: DetailPokemon & { onClose: () => void },
) {
  return (
    <Modal title={pokemonTitle(props.pokemon)} onClose={props.onClose}>
      <div className="detail-identity">
        <PokemonSprite species={props.pokemon.species} large />
        <div>
          <span className="eyebrow">
            {props.visibility === "self" ? "TU POKÉMON" : "EQUIPO PÚBLICO"}
          </span>
          <h3>{pokemonName("species", props.pokemon.species)}</h3>
          <p>Nivel {props.pokemon.level ?? "—"}</p>
        </div>
      </div>
      <PokemonDetails {...props} />
    </Modal>
  );
}
export function PokemonDetails(props: DetailPokemon) {
  const p = props.pokemon;
  return (
    <>
      <dl className="details">
        <dt>Especie</dt>
        <dd>{pokemonName("species", p.species)}</dd>
        <dt>Nivel</dt>
        <dd>{p.level ?? "—"}</dd>
        <dt>Tipos</dt>
        <dd>
          {p.types?.length ? (
            <div className="tags">
              {p.types.map((t) => (
                <TypeBadge key={t} type={t} />
              ))}
            </div>
          ) : (
            "—"
          )}
        </dd>
        <dt>Objeto</dt>
        <dd>
          {p.item ? (
            <span className="held-item">
              <ItemIcon name={p.item} />
              {pokemonName("item", p.item)}
            </span>
          ) : (
            "Sin objeto"
          )}
        </dd>
      </dl>
      <h3>Movimientos</h3>
      <div className="moves">
        {p.moves?.length
          ? p.moves.map((m, i) => <MovePopover key={i} name={m.name} />)
          : "No disponibles."}
      </div>
      {props.visibility === "self" && (
        <>
          <dl className="details">
            <dt>Habilidad</dt>
            <dd>
              {props.pokemon.ability
                ? pokemonName("ability", props.pokemon.ability)
                : "—"}
            </dd>
            <dt>Naturaleza</dt>
            <dd>
              {props.pokemon.nature
                ? pokemonName("nature", props.pokemon.nature)
                : "—"}
            </dd>
          </dl>
          {(["ivs", "evs"] as const).map((k) => (
            <div key={k}>
              <h3>{k.toUpperCase()}</h3>
              {props.pokemon[k] ? (
                <dl className="stats-list">
                  {Object.entries(props.pokemon[k]!).map(([stat, v]) => (
                    <div key={stat}>
                      <dt>{statName(stat)}</dt>
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
