# Module Inventory

Clasificacion inicial tras auditoria. Esta lista debe actualizarse cuando se
extraiga dominio o repositories.

## Root

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `main.py` | STREAMLIT | Configuracion, shell, login, sidebar, topbar y router. |
| `utils.py` | MIXED | Roster, secciones, session_state, saves locales y helpers. |
| `storage.py` | STORAGE/LEGACY | Fachada de Supabase/SQLite/settings/saves/wipe. |
| `conex_pkhex.py` | MIXED | Bridge/parser PKHeX, cache y normalizacion a UI. |
| `dexdata.py` | MIXED | Datos Pokemon, cache local y traducciones. |
| `saves.py` | STREAMLIT | UI de subida/historial/wipe de saves. |
| `tienda2.py` | LEGACY WRAPPER | Wrapper a `app.tienda.ui`. |
| `liga_tabla.py` | LEGACY WRAPPER | Wrapper de liga/tabla. |
| `entrenadores.py` | LEGACY WRAPPER | Wrapper a entrenadores. |

## app/season

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `config.py` | MIXED | Buen inicio de SeasonVersion, pero lee/escribe `settings`. |
| `validation.py` | PURE | Validaciones casi portables a dominio. |

## app/liga

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `ranking.py` | MIXED | Logica valiosa, pero depende de Streamlit, saves y storage. |
| `state.py` | STREAMLIT/STORAGE | Serializa `st.session_state` a `settings.league_state`. |
| `rewards.py` | PURE-ish | Delegacion simple a season config. |
| `divisions.py` | PURE-ish | Ascensos/descensos, portable si se inyecta config. |
| `ui.py` | STREAMLIT | Pantalla pesada de gestion liga. |
| `matchup.py` | STREAMLIT/MIXED | Team Preview con UI, snapshots y detalle de ataques. |

## app/tienda

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `discounts.py` | PURE-ish/MIXED | Seleccion de promociones reutilizable; persiste y avisa Discord. |
| `catalog_data.py` | PURE-ish | Catalogo estatico con assets. |
| `catalog_render.py` | STREAMLIT/HTML | Render de cards; el CTA usa `st.button` fuera del HTML de la card y se integra visualmente con CSS hasta extraer `ShopItemCard`. |
| `sections.py` | STREAMLIT | Vista tienda y flujo de compra; confirmacion y compra siguen acopladas a `st.session_state`. |
| `redeem.py` | MIXED | Canje de objetos, flags, saves y UI. |
| `money.py` | MIXED | Calculo monedas con snapshots, medallas y compras. |
| `styles.py` | STREAMLIT/CSS | Estilos tienda. |

## app/entrenadores

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `page.py` | STREAMLIT | Pantalla principal grande; concentra CSS local de Entrenadores/PC/Inspector hasta extraer design system. |
| `boxes.py` | STREAMLIT/MIXED | PC/Cajas, seleccion y mapping de slots; el orden real del save esta acoplado al render. |
| `snapshot.py` | MIXED/STORAGE | Snapshot derivado de save, guardado en settings. |
| `trainer_flags.py` | MIXED/STORAGE | Robado/retirado sobre settings + redemptions. |
| `cache.py` | MIXED | Cache del parser PKHeX. |
| `detail_render.py` | STREAMLIT/HTML | Inspector visual; reutiliza resolver de iconos de inventario temporalmente. |
| `summary.py` | STREAMLIT/MIXED | Resumen, monedas, puntos, medallas. |
| `inventory.py` | STREAMLIT/MIXED | Inventario y canjes. |

## app/interfaz

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `theme.py` | STREAMLIT/CSS | Base visual y aplica capas posteriores. |
| `champions_skin.py` | STREAMLIT/CSS | Capa principal estilo Champions. |
| `premium_phase2.py` | STREAMLIT/CSS | Capa visual 2.0 acumulada. |
| `final_polish.py` | STREAMLIT/CSS | Parches visuales finales. |
| `auth.py` | STREAMLIT/STORAGE | Login y PIN via settings. |
| `sidebar.py` | STREAMLIT/STORAGE | Navegacion, PIN, perfil mini. |
| `home.py` | STREAMLIT/MIXED | Menu principal y resumen. |
| `notifications.py` | MIXED | Actividad reciente desde saves, compras y locks. |
| `temporada.py` | STREAMLIT/MIXED | Editor admin sobre season config. |
| `hall_of_fame.py` | MIXED | Logica y UI de historico. |

## app/storage_*

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `storage_shop.py` | STORAGE | Compras, promociones, locks, inventario, redenciones. |
| `storage_flags.py` | STORAGE | Flags de Pokemon y limpieza. |
| `storage_cache.py` | STORAGE | Cache simple en memoria. |

## Tests Actuales

| Test | Cobertura |
| --- | --- |
| `test_shop_promotions.py` | Rebajas, exclusiones y rotacion. |
| `test_season_config.py` | Versionado de temporada. |
| `test_season_validation.py` | Validacion de temporada. |
| `test_notifications.py` | Actividad reciente y limite visible. |
| `test_liga_rewards.py` | Recompensas y divisiones actuales. |
| `test_hall_of_fame.py` | Coercion/merge de historico. |
| `test_saves_support.py` | HTML de saves. |
