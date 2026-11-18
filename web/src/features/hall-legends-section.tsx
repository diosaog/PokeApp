import type { CSSProperties } from "react";
import { Crown, Trophy } from "lucide-react";
import { pokemonName } from "../pokemon/localization";
import {
  PokemonSprite,
  SpriteGeneration,
  TrainerPhoto,
} from "../pokemon/presentation";
import { legends } from "./hall-legends";

const titles = (n: number) => (n === 1 ? "1 título" : `${n} títulos`);

/**
 * Hall de la Fama › Leyendas: the champions of the competitions played before
 * PokeApp. One showcase per trainer, ranked by titles: the portrait on its
 * pedestal, then each title in the colours of its game with the team that
 * won it, only as moving sprites (no moves, items or stats). Static content:
 * see hall-legends.ts. Sprites use the battle models (Gen7 art) so every
 * team, Gen7 Pokémon and alternate forms included, moves in one style.
 */
export function HallLegends() {
  const ranked = [...legends].sort((a, b) => b.titles.length - a.titles.length);
  return (
    <section className="legends" aria-labelledby="legends-title">
      <header className="legends-head">
        <span className="eyebrow">ANTES DE POKEAPP</span>
        <h2 id="legends-title">Leyendas</h2>
        <p>
          Los campeones de nuestras partidas anteriores, con el equipo que los
          llevó a la gloria.
        </p>
      </header>
      <SpriteGeneration value={7}>
        <ol className="legends-list">
          {ranked.map((legend, index) => (
            <li
              key={legend.trainer}
              className="legend-showcase"
              aria-label={`${legend.trainer}, ${titles(legend.titles.length)}`}
            >
              <div className="legend-champion">
                <span className="legend-rank" aria-hidden="true">
                  {index + 1}
                </span>
                <div className="legend-portrait">
                  <TrainerPhoto name={legend.trainer} />
                  <span className="legend-medal" aria-hidden="true">
                    <Crown />
                  </span>
                </div>
                <div className="legend-champion-text">
                  <h3>{legend.trainer}</h3>
                  <span>{titles(legend.titles.length)}</span>
                  <span className="legend-trophies" aria-hidden="true">
                    {legend.titles.map((t) => (
                      <Trophy key={t.id} />
                    ))}
                  </span>
                </div>
              </div>
              <div className="legend-titles">
                {legend.titles.map((title) => (
                  <article
                    key={title.id}
                    className={`legend-card legend-${title.theme}`}
                    aria-label={`${legend.trainer}, ${
                      title.kind === "copa" ? "campeón de la" : "campeón de"
                    } ${title.series} ${title.game}`}
                  >
                    <span className="legend-kind">Campeón</span>
                    <h4 className="legend-game">
                      <small>{title.series}</small>
                      {title.game}
                    </h4>
                    <ul
                      className="legend-team"
                      aria-label={`Equipo campeón de ${legend.trainer}`}
                    >
                      {title.team.map((pokemon, i) => (
                        <li
                          key={`${pokemon.species}-${i}`}
                          title={
                            pokemon.label ??
                            pokemonName("species", pokemon.species)
                          }
                          style={{ "--i": i } as CSSProperties}
                        >
                          <PokemonSprite
                            species={pokemon.species}
                            form={pokemon.form}
                            animated
                            large
                          />
                        </li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </li>
          ))}
        </ol>
      </SpriteGeneration>
    </section>
  );
}
