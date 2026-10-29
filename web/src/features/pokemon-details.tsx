import type { Model } from "../api/types";
import { catalogId, pokemonName, pokemonTitle } from "../pokemon/localization";
import {
  ItemIcon,
  MoveLabel,
  PokemonSprite,
  TypeBadge,
  IVBars,
  typeClass,
} from "../pokemon/presentation";
import { Modal } from "../ui";
type Public = Pick<
  Model<"PokemonRead">,
  | "species"
  | "nickname"
  | "level"
  | "types"
  | "item"
  | "form"
  | "item_generation"
> & { moves?: { name: string }[] | null; is_shiny?: boolean };
export type DetailPokemon =
  | { visibility: "public"; pokemon: Public }
  | { visibility: "self"; pokemon: Model<"PrivatePokemonRead"> };
export function PokemonDetailModal(
  props: DetailPokemon & { onClose: () => void },
) {
  return (
    <Modal title={pokemonTitle(props.pokemon)} onClose={props.onClose}>
      <PokemonDetails {...props} />
    </Modal>
  );
}
export function PokemonDetails(props: DetailPokemon) {
  const p = props.pokemon;
  const dex = catalogId("species", p.species);
  return (
    <div className={`pokemon-detail-layout ${typeClass(p.types?.[0])}`}>
      <section className="detail-identity">
        <span className="eyebrow">
          {props.visibility === "self" ? "TU POKÉMON" : "POKÉMON PÚBLICO"}
        </span>
        {/* Pokédex-style stage: the Pokémon on its type colour. */}
        <div className="dex-stage">
          <PokemonSprite
            species={p.species}
            form={p.form}
            shiny={p.is_shiny}
            large
            animated
          />
        </div>
        {dex && (
          <span className="dex-number">Nº {String(dex).padStart(3, "0")}</span>
        )}
        <h3>{pokemonName("species", p.species)}</h3>
        {!!p.form && <p>Forma {p.form}</p>}
        <p className="dex-level">Nivel {p.level ?? "—"}</p>
        <div className="tags">
          {p.types?.map((t) => (
            <TypeBadge key={t} type={t} />
          ))}
        </div>
      </section>
      <section className="detail-data" aria-label="Características">
        {props.visibility === "self" && (
          <>
            <h3>IVs</h3>
            <IVBars values={props.pokemon.ivs} />
          </>
        )}
        <dl className="detail-traits">
          {props.visibility === "self" && (
            <>
              <div>
                <dt>Habilidad</dt>
                <dd>
                  {props.pokemon.ability
                    ? pokemonName("ability", props.pokemon.ability)
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>Naturaleza</dt>
                <dd>
                  {props.pokemon.nature
                    ? pokemonName("nature", props.pokemon.nature)
                    : "—"}
                </dd>
              </div>
            </>
          )}
          <div>
            <dt>Objeto equipado</dt>
            <dd>
              {p.item ? (
                <span className="held-item">
                  <ItemIcon
                    name={pokemonName(
                      "item",
                      p.item,
                      p.item_generation ?? undefined,
                    )}
                  />
                  {pokemonName("item", p.item, p.item_generation ?? undefined)}
                </span>
              ) : (
                "Sin objeto"
              )}
            </dd>
          </div>
        </dl>
      </section>
      <section className="detail-moves" aria-label="Movimientos">
        <h3>Movimientos</h3>
        {Array.from({ length: 4 }, (_, i) =>
          p.moves?.[i] ? (
            <MoveLabel key={i} name={p.moves[i].name} />
          ) : (
            <div className="move-vacant" key={i}>
              No disponible
            </div>
          ),
        )}
      </section>
    </div>
  );
}
