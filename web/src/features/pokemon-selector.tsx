import { useMemo, useState } from "react";
import type { Model } from "../api/types";
import { pokemonName, pokemonTitle } from "../pokemon/localization";
import { PokemonSprite, PokemonStatusFlags } from "../pokemon/presentation";
import { Empty, Modal, Tag } from "../ui";

// A target the server shows but refuses (blindado, recién capturado…) carries
// the reason: it stays visible, explained, and cannot be chosen.
export type PokemonTarget = Model<"TargetRead"> & {
  blocked?: string | null;
  message?: string | null;
  available_at?: string;
};

type PokemonSelectorModalProps = {
  title: string;
  targets: PokemonTarget[];
  onClose: () => void;
  onConfirm: (target: PokemonTarget) => void | Promise<void>;
  confirmLabel: string;
  confirmation: (target: PokemonTarget) => string;
  emptyText?: string;
};

function boxNumber(location: string) {
  const match = location.match(/^Caja\s+(\d+)/i);
  return match ? Number(match[1]) : null;
}

function isParty(location: string) {
  return location.toLowerCase().startsWith("equipo");
}

// «Faltan 3 h 20 min» while the 24 h since the first verified sighting run out.
function remaining(availableAt?: string) {
  const left = availableAt ? new Date(availableAt).getTime() - Date.now() : 0;
  if (!(left > 0)) return "";
  const minutes = Math.ceil(left / 60000);
  const hours = Math.floor(minutes / 60);
  return hours
    ? ` Faltan ${hours} h ${minutes % 60} min.`
    : ` Faltan ${minutes} min.`;
}

function TargetCard({
  target,
  selected,
  onSelect,
}: {
  target: PokemonTarget;
  selected: boolean;
  onSelect: () => void;
}) {
  const refused = Boolean(target.blocked);
  return (
    <button
      type="button"
      className={`pokemon-selector-card${selected ? " is-selected" : ""}`}
      aria-pressed={selected}
      disabled={refused}
      onClick={onSelect}
    >
      <PokemonSprite
        species={target.pokemon.species}
        form={target.pokemon.form}
      />
      <span className="pokemon-selector-copy">
        <strong>{pokemonTitle(target.pokemon)}</strong>
        <small>
          {target.pokemon.nickname
            ? pokemonName("species", target.pokemon.species)
            : "Pokémon"}
          {target.pokemon.level != null && ` · Nv. ${target.pokemon.level}`}
        </small>
        <span className="muted">{target.location}</span>
        <PokemonStatusFlags flags={target.pokemon.status_flags} />
        {refused && (
          <span className="muted">
            {target.message}
            {target.blocked === "recent_capture" &&
              remaining(target.available_at)}
          </span>
        )}
      </span>
    </button>
  );
}

export function PokemonSelectorModal({
  title,
  targets,
  onClose,
  onConfirm,
  confirmLabel,
  confirmation,
  emptyText = "No hay Pokémon disponibles para este canje.",
}: PokemonSelectorModalProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [boxIndex, setBoxIndex] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const party = useMemo(
    () => targets.filter((target) => isParty(target.location)),
    [targets],
  );
  const boxes = useMemo(() => {
    const grouped = new Map<number, PokemonTarget[]>();
    for (const target of targets) {
      const number = boxNumber(target.location);
      if (number == null) continue;
      const current = grouped.get(number) || [];
      current.push(target);
      grouped.set(number, current);
    }
    return [...grouped.entries()].sort(([a], [b]) => a - b);
  }, [targets]);
  const selected =
    targets.find((target) => target.pokemon_entity_id === selectedId) || null;
  const currentBox = boxes[boxIndex];

  return (
    <Modal title={title} onClose={onClose}>
      {!targets.length ? (
        <Empty>{emptyText}</Empty>
      ) : confirming && selected ? (
        <div className="pokemon-selector-confirm">
          <TargetCard
            target={selected}
            selected
            onSelect={() => setConfirming(false)}
          />
          <p className="selector-confirmation">{confirmation(selected)}</p>
          <div className="selector-actions">
            <button type="button" onClick={() => setConfirming(false)}>
              Cancelar
            </button>
            <button
              type="button"
              className="button primary"
              onClick={() => void onConfirm(selected)}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      ) : (
        <div className="pokemon-selector">
          <p className="muted">Selecciona un Pokémon para continuar.</p>
          {party.length > 0 && (
            <section>
              <div className="selector-section-heading">
                <h3>Equipo</h3>
                <Tag>{party.length}</Tag>
              </div>
              <div className="pokemon-selector-grid party-selector-grid">
                {party.map((target) => (
                  <TargetCard
                    key={target.pokemon_entity_id}
                    target={target}
                    selected={target.pokemon_entity_id === selectedId}
                    onSelect={() => {
                      setSelectedId(target.pokemon_entity_id);
                      setConfirming(true);
                    }}
                  />
                ))}
              </div>
            </section>
          )}
          {currentBox && (
            <section>
              <div className="selector-section-heading">
                <h3>Caja {currentBox[0]}</h3>
                {boxes.length > 1 && (
                  <div className="selector-box-controls">
                    <button
                      type="button"
                      aria-label="Caja anterior"
                      onClick={() =>
                        setBoxIndex(
                          (boxIndex - 1 + boxes.length) % boxes.length,
                        )
                      }
                    >
                      ‹
                    </button>
                    <span>
                      {boxIndex + 1} / {boxes.length}
                    </span>
                    <button
                      type="button"
                      aria-label="Caja siguiente"
                      onClick={() => setBoxIndex((boxIndex + 1) % boxes.length)}
                    >
                      ›
                    </button>
                  </div>
                )}
              </div>
              <div className="pokemon-selector-grid box-selector-grid">
                {currentBox[1].map((target) => (
                  <TargetCard
                    key={target.pokemon_entity_id}
                    target={target}
                    selected={target.pokemon_entity_id === selectedId}
                    onSelect={() => {
                      setSelectedId(target.pokemon_entity_id);
                      setConfirming(true);
                    }}
                  />
                ))}
              </div>
            </section>
          )}
          {!party.length && !boxes.length && <Empty>{emptyText}</Empty>}
        </div>
      )}
    </Modal>
  );
}
