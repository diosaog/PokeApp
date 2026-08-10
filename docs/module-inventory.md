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
| `saves.py` | STREAMLIT | UI de subida/historial/wipe de saves; render apoyado en `app/saves_support.py` para cards y CSS 1D. |
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
| `ui.py` | STREAMLIT | Pantalla pesada de gestion liga; el render de divisiones consume puntos/monedas/badges para la vista deportiva 1D. |
| `matchup.py` | STREAMLIT/MIXED | Team Preview con UI, snapshots y detalle de ataques. |

## app/copa

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `styles.py` | STREAMLIT/CSS | Shell visual de Copa suiza/eliminatoria; pulido 1E como match center, pendiente extraer componentes visuales. |
| `swiss.py` | STREAMLIT/MIXED | Gestion de rondas, clasificacion, equipos y Top Cut. |
| `elim.py` | STREAMLIT/MIXED | Eliminatoria Bo3 con bracket editable. |
| `doubles.py` | STREAMLIT/MIXED | Copa Dobles mantiene estado en settings; CSS local pulido 1E, pendiente converger con `styles.py`. |
| `logos.py` | ASSET HELPER | Resolucion local de logos de equipos. |

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

## app/juicios

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `ui.py` | STREAMLIT/MIXED | Bandeja, filtros, formularios y acciones de expedientes; CSS local 1E con cards de expediente. |
| `render.py` | STREAMLIT/HTML | Detalle de expediente y castigos; presentacion refinada 1E sin tocar reglas de voto. |
| `repo.py` | STORAGE/MIXED | Persistencia y permisos de juicios. |
| `forms.py` | STREAMLIT | Formularios de alta, edicion y resolucion. |
| `penalties.py` | MIXED | Lectura de sanciones activas y efectos en tienda/monedas. |

## app/interfaz

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `theme.py` | STREAMLIT/CSS | Base visual y aplica capas posteriores. |
| `champions_skin.py` | STREAMLIT/CSS | Capa principal estilo Champions. |
| `premium_phase2.py` | STREAMLIT/CSS | Capa visual 2.0 acumulada. |
| `final_polish.py` | STREAMLIT/CSS | Parches visuales finales; incluye capa 1E para pantallas secundarias. |
| `auth.py` | STREAMLIT/STORAGE | Login y PIN via settings. |
| `sidebar.py` | STREAMLIT/STORAGE | Navegacion, PIN, perfil mini. |
| `home.py` | STREAMLIT/MIXED | Menu principal y resumen. |
| `notifications.py` | MIXED | Actividad reciente desde saves, compras y locks. |
| `normativa.py` | STREAMLIT/CONTENT | Manual oficial con render por articulos 1E; texto funcional conservado. |
| `temporada.py` | STREAMLIT/MIXED | Editor admin sobre season config; pulido 1E como consola tecnica compacta. |
| `hall_of_fame.py` | MIXED | Logica y UI de historico; archivo sobrio con auto-sync de campeones. |

### Auditoria visual 1F

| Zona | Estado | Nota |
| --- | --- | --- |
| Cascada global | DEUDA | `theme.py`, `champions_skin.py`, `premium_phase2.py` y `final_polish.py` siguen conviviendo. La deuda principal no es falta de clases, sino selectores antiguos con `.main` + `!important` que pueden ganar a parches finales mas nuevos. |
| Normativa | CORREGIDO | La capa 1E existia, pero `theme.py`/`champions_skin.py` ganaban por especificidad. `final_polish.py` ahora usa `.main .norma-*` y se elimino el `st.header` duplicado de la pagina. |
| Team Preview | CORREGIDO | Los overrides finales de board, cartas, ataques, sprites y detalle de movimiento pasan a `.main .battle-*` / `.main .matchup-*` para no caer en el estilo Champions antiguo claro/morado. |
| Tienda | CORREGIDO | El pulido final de cards, precios, rebajas y cabecera se refuerza con `.main` para ganar a `app/tienda/styles.py` sin tocar logica de compra ni promociones. |
| Entrenadores / PC | CORREGIDO | Equipo actual, chips y tiles de PC quedan protegidos por selectores finales con `.main`; queda pendiente extraer `TrainerCard` y `BoxTile` al futuro sistema de componentes. |
| Liga / Hall / Saves | CORREGIDO | Superficies, tablas, badges y estados vacios quedan bajo selectores finales con `.main`. |
| Pendiente React/Cloudflare | DIFERIDO | Retirar las capas CSS acumuladas y mover estos patrones a componentes/tokens reales antes de optimizar render y routing. |

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
