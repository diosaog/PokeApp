import { useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import type { Model } from "../api/types";
import { Card, Empty } from "../ui";
import { PokemonSprite, PokemonStatusFlags } from "../pokemon/presentation";
import { pokemonTitle, pokemonName } from "../pokemon/localization";
import { PokemonDetailModal, type DetailPokemon } from "./pokemon-details";

export function collectionLocation(value: string) {
  const team = /^Equipo · (\d+)$/.exec(value);
  const box = /^Caja (\d+) · (\d+)$/.exec(value);
  return team
    ? { box: 0, slot: Number(team[1]) }
    : box
      ? { box: Number(box[1]), slot: Number(box[2]) }
      : null;
}
export function Collection({
  slots,
  showDead = false,
  visibility = "self",
}: {
  slots: (Model<"SlotRead"> | Model<"PublicSlotRead">)[];
  visibility?: "self" | "public";
  showDead?: boolean;
}) {
  const [index, setIndex] = useState(0),
    [search, setSearch] = useState("");
  const [selected, setSelected] = useState<DetailPokemon | null>(null);
  const located = slots.map((s) => ({
    ...s,
    position: collectionLocation(s.location),
  }));
  // The API omits empty boxes. Count only boxes with observed content, never
  // invent a total save capacity or infer emptiness of unpublished boxes.
  const boxes = [
    ...new Set(
      located.flatMap((s) => (s.position?.box ? [s.position.box] : [])),
    ),
  ].sort((a, b) => a - b);
  const current = Math.min(index, Math.max(0, boxes.length - 1)),
    box = boxes[current];
  const moveBox = (delta: number) => {
    if (boxes.length <= 1) return;
    setIndex((current + delta + boxes.length) % boxes.length);
  };
  const team = located.filter((s) => s.position?.box === 0);
  const inBox = located.filter((s) => s.position?.box === box);
  function slot(
    p: Model<"PrivatePokemonRead"> | Model<"PokemonRead"> | undefined,
    key: number,
    label: string,
    animated = false,
  ) {
    return p ? (
      <button
        className="pc-slot pokemon"
        key={key}
        onClick={() =>
          setSelected(
            visibility === "self" && "ability" in p && "nature" in p
              ? { visibility: "self", pokemon: p }
              : { visibility: "public", pokemon: p },
          )
        }
        aria-label={`${pokemonTitle(p)} · ${label}`}
      >
        <PokemonSprite species={p.species} form={p.form} animated={animated} />
        <PokemonStatusFlags flags={p.status_flags} />
        <span>{pokemonTitle(p)}</span>
        <small>Nv. {p.level ?? "—"}</small>
        {!!p.form && <small>Forma {p.form}</small>}
      </button>
    ) : (
      <div
        className="pc-slot vacant"
        key={key}
        aria-label={`${label}: sin Pokémon`}
      >
        <span>·</span>
      </div>
    );
  }
  const found = located.filter((s) =>
    `${pokemonName("species", s.pokemon.species)} ${s.pokemon.nickname}`
      .toLocaleLowerCase("es")
      .includes(search.toLocaleLowerCase("es")),
  );
  return (
    <div className="collection">
      <Card className="party-panel">
        <div className="section-row">
          <h2>Equipo</h2>
          <span className="caption">{team.length} / 6</span>
        </div>
        <div className="party-slots">
          {Array.from({ length: 6 }, (_, i) =>
            slot(
              team.find((s) => s.position?.slot === i + 1)?.pokemon,
              i,
              `Equipo ${i + 1}`,
              true,
            ),
          )}
        </div>
      </Card>
      <Card className="box-panel">
        <div className="box-toolbar">
          <div className="box-controls">
            <button
              className="icon-button"
              aria-label="Caja anterior"
              disabled={boxes.length <= 1}
              onClick={() => moveBox(-1)}
            >
              <ChevronLeft />
            </button>
            <div>
              <h2>
                {box ? `Caja ${box}` : "Cajas"}
                {box === 8 && <small> · Muertos</small>}
              </h2>
              <span className="caption">
                {boxes.length
                  ? `${current + 1} / ${boxes.length} cajas con Pokémon`
                  : "Sin cajas con Pokémon"}
              </span>
            </div>
            <button
              className="icon-button"
              aria-label="Caja siguiente"
              disabled={boxes.length <= 1}
              onClick={() => moveBox(1)}
            >
              <ChevronRight />
            </button>
          </div>
          <label className="pc-search">
            <Search size={16} />
            <input
              type="search"
              aria-label="Buscar Pokémon"
              placeholder="Buscar especie o apodo"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
        </div>
        {search ? (
          <>
            <p className="caption">
              {found.length} coincidencias
              {found.length > 30 ? " · Primeras 30" : ""}
            </p>
            <div className="box-slots">
              {found.slice(0, 30).map((s, i) => slot(s.pokemon, i, s.location))}
            </div>
            {!found.length && <Empty>No hay coincidencias.</Empty>}
          </>
        ) : box ? (
          <div className="box-slots" aria-label={`Contenido de Caja ${box}`}>
            {Array.from({ length: 30 }, (_, i) =>
              slot(
                inBox.find((s) => s.position?.slot === i + 1)?.pokemon,
                i,
                `Caja ${box}, posición ${i + 1}`,
              ),
            )}
          </div>
        ) : (
          <Empty>Todavía no hay Pokémon en las cajas disponibles.</Empty>
        )}
      </Card>
      {showDead && (
        <Card>
          <h2>Muertos</h2>
          <p className="muted">Pokémon observados en la caja de muertos.</p>
          <div className="dead-slots">
            {located
              .filter((s) => s.position?.box === 8)
              .map((s, i) => slot(s.pokemon, i, s.location))}
          </div>
          {!located.some((s) => s.position?.box === 8) && (
            <p className="muted">
              No hay Pokémon en la caja de muertos de esta partida.
            </p>
          )}
        </Card>
      )}
      {selected && (
        <PokemonDetailModal {...selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
