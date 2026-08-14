# PokeApp Domain Model

Este documento define los conceptos que deben sobrevivir a Streamlit y poder ser
consumidos por tests, API, React o cualquier cliente futuro.

## Entidades Principales

### Trainer

- `id`
- `name`
- `pin_hash` o credencial equivalente
- `status`: active, retired
- `flags`: robbed, retired, penalties
- `current_save_id`
- `season_memberships`

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
- `status`: draft, active, finished, archived
- `created_at`
- `started_at`
- `finished_at`
- `active_version_id`

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
- `type`: save_uploaded, purchase, team_locked, season_changed, retired, round_closed
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

### Trial / Case

- `id`
- `season_id`
- `accused`
- `created_by`
- `status`
- `penalties`
- `created_at`
- `resolved_at`
