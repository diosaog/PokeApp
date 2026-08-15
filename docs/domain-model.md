# PokeApp Domain Model

Este documento define los conceptos que deben sobrevivir a Streamlit y poder ser
consumidos por tests, API, React o cualquier cliente futuro.

## Entidades Principales

### Trainer

- `id`
- `name`
- `pin_hash` o credencial equivalente
- `status`: active, retired, abandoned, disqualified
- `flags`: robbed, penalties, cosmetic/status markers that do not remove the
  trainer from competition by themselves
- `current_save_id`
- `season_memberships`

Estado Streamlit 2.3:

- `trainer_flags` sigue viviendo como JSON en `settings`.
- `retired`, `abandoned` y `disqualified` son TrainerStatus administrativos.
- `robbed` sigue siendo TrainerFlag funcional de tienda/redemptions.
- La app mantiene `is_trainer_retired()` como compatibilidad, pero semánticamente
  significa "entrenador inactivo".
- No existe reactivacion automatica: los estados inactivos son permanentes para
  las reglas actuales.

### Pokemon

- `id` o fingerprint estable cuando exista
- `species`
- `nickname`
- `level`
- `gender`
- `types`
- `item`
- `ability`
- `nature`
- `ivs`
- `evs`
- `moves`
- `box`
- `slot`
- `status`: alive, dead, shielded, stolen, revived

Separar contrato publico y privado:

- `PublicPokemon`: sin IVs, EVs, naturaleza privada ni datos ocultos.
- `PrivatePokemon`: equipo propio completo para el entrenador autenticado.

### ParsedSave

Salida normalizada del parser/bridge:

- `trainer`
- `party`
- `boxes`
- `badges`
- `metadata`
- `dead_count`
- `raw_source`

La app no debe depender de detalles internos de PKHeX. Si cambia el parser, se
mantiene este contrato.

### Season

- `season_id`
- `name`
- `status`: draft, active, finished, archived, discarded
- `created_at`
- `started_at`
- `finished_at`
- `active_version_id`

Estado Streamlit 2.4:

- No hay `season_id` real todavía.
- El lifecycle se guarda en `settings.season_lifecycle_v1`.
- El ciclo funcional es `active -> finished -> archived -> nueva active`, con
  `discarded` como salida sin archivo.
- `finished` permite revisar antes de archivar.
- `archived` exige un `SeasonArchive`.

### SeasonArchive

Snapshot historico autosuficiente de una temporada cerrada.

- `id`
- `label`
- `state`
- `started_at`
- `finished_at`
- `archived_at`
- `participants`
- `trainer_statuses`
- `season_config`
- `season_version_used`
- `max_rounds`
- `league`
- `team_locks`
- `champion_team`
- `cup`
- `hall_entries`
- `metadata`

Estado Streamlit 2.4:

- Se persiste en `settings.season_archives_v1`.
- Es temporal pre-Supabase V2, pero explicito e inmutable por defecto.
- No copia todo `settings`; solo datos competitivos necesarios.
- Hall of Fame puede derivar de `hall_entries` archivadas.

### SeasonVersion

Representa reglas aplicables desde una jornada concreta.

- `id`
- `season_id`
- `effective_round`
- `max_rounds`
- `players`
- `division_count`
- `division_sizes`
- `movement_count`
- `points_by_position`
- `coins_by_position`
- `rules`

Esto permite cambiar reglas desde una jornada sin alterar resultados antiguos.

Estado Streamlit 2.2:

- `season_config_v2` ya versiona estos campos en `settings`.
- Las jornadas cerradas usan `round_snapshots` como fuente historica.
- La implementacion Streamlit soporta oficialmente dos divisiones, A/B. N
  divisiones requiere el contrato `Division`/`Matchday` real antes de migrar a
  API.

### Division

- `season_id`
- `round_no`
- `name`
- `players`
- `order`

### Matchday

- `season_id`
- `round_no`
- `status`: draft, active, closed
- `version_id`
- `opened_at`
- `closed_at`

### Match

- `season_id`
- `round_no`
- `division`
- `player_a`
- `player_b`
- `winner`
- `status`

### LeagueStanding

- `season_id`
- `round_no`
- `trainer`
- `position`
- `points`
- `coins`
- `dead_penalty`
- `penalty_points`

### TeamLock

- `season_id`
- `round_no`
- `trainer`
- `save_id`
- `team`
- `locked_at`
- `deadline_at`
- `is_late`

### ShopItem

- `id`
- `name`
- `category`
- `base_price`
- `description`
- `image`
- `active`
- `rules`

### ShopPromotion

- `id`
- `season_id`
- `round_no`
- `item_id`
- `kind`: normal, mega
- `base_price`
- `discount_price`
- `stock_total`
- `stock_used`
- `announced_at`
- `activates_at`
- `active`

### Purchase

- `id`
- `season_id`
- `trainer`
- `item_id`
- `price`
- `base_price`
- `promotion_id`
- `status`
- `created_at`
- `redeemed_at`

### ActivityEvent

- `id`
- `season_id`
- `type`: save_uploaded, purchase, team_locked, season_changed, trainer_status_changed, round_closed
- `actor`
- `target`
- `summary`
- `metadata`
- `created_at`

### HallOfFameEntry

- `id`
- `season_id`
- `competition`
- `champion`
- `title`
- `team`
- `created_at`
- `source`

Estado Streamlit 2.4:

- Legacy sigue en `settings.hall_of_fame_v1`.
- Las entradas nuevas pueden venir de `SeasonArchive`.
- El equipo campeon se congela como snapshot publico: species, nickname, level,
  gender, item, types y moves.
- No se guardan IVs, EVs, naturaleza ni habilidad privada en Hall.

### Trial / Case

- `id`
- `season_id`
- `accused`
- `created_by`
- `status`
- `penalties`
- `created_at`
- `resolved_at`
