# Post-2.0 Backlog

This document is the parking lot for ideas after the functional freeze.

Rule: do not implement items from this backlog until the architecture migration
plan reaches the correct phase. Bugs, security fixes, equivalence work and
stability fixes are allowed; new mechanics are not.

## Deferred Ideas

| Idea | Why deferred | Earliest phase |
| --- | --- | --- |
| True N divisions | Current Streamlit product is officially A/B. N divisions need new domain contracts, state shape, history and UI. | Fase 3+ |
| Setup wizard for new seasons | Current config/admin is enough for 2.0; a polished draft/start flow belongs after contracts. | Fase 3+ |
| Supabase Storage/Auth staging validation | SQL and RLS already passed real Postgres validation; Supabase-specific Auth/Storage behavior still needs staging before cutover. | Fase 8+ |
| API hardening | Requires critical operation design over the secured V2 schema. | Fase 8 |
| React / Cloudflare app | Should be built after contracts, domain, repositories, V2 schema, RLS/API and parser boundary. | Fase 10 |
| Copa as typed domain | Current Copa works as legacy settings state, but migration needs `Cup` entities. | Fase 3+ |
| Juicios as typed domain | Current Juicios works, but migration needs `Trial / Case` entities, tests and permissions. | Fase 3+ |
| Component design system | Streamlit visual is frozen; reusable cards/tiles/menus should be extracted during frontend migration. | Fase 10 |
| More ActivityEvent types | Current visible events are enough. More events should be emitted server-side later. | Fase 8+ |
| Performance optimization | Measure after domain/repository/API boundaries exist. | Fase 14 |

## Do Not Add Here As Urgent

- Small cosmetic preferences.
- New shop mechanics.
- New league formats before N-division contracts.
- Discord announcement changes unless they support an existing frozen mechanic.
