import { useMemo, useState } from "react";
import type { Model } from "../api/types";
import { pokemonName, pokemonTitle } from "../pokemon/localization";
import { PokemonSprite, PokemonStatusFlags } from "../pokemon/presentation";
import { Empty, Modal, Tag } from "../ui";

export type PokemonTarget = Model<"TargetRead">;

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

function TargetCard({
  target,
  selected,
  onSelect,
}: {
  target: PokemonTarget;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={`pokemon-selector-card${selected ? " is-selected" : ""}`}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <PokemonSprite
        species={target.pokemon.species}
        animated={isParty(target.location)}
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
