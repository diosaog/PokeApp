# PokeApp 2.0 - Protocolo Maestro de Proyecto y Handoff Multi-IA

**Documento operativo para ChatGPT, Codex, Gemini y cualquier agente de ingeniería que continúe el proyecto.**  
**Versión de referencia:** 26 de septiembre de 2026.  
**Idioma de trabajo con el Product Owner:** español.

> Este documento NO es una orden para implementar una fase concreta. Es el contrato operativo y de contexto que debe leer cualquier IA antes de continuar PokeApp 2.0. La tarea concreta de cada fase se añadirá aparte.

---

# 0. Cómo usar este documento

Este documento existe para que el proyecto no dependa de la memoria de un chat concreto ni de una IA concreta. PokeApp puede ser continuada de forma secuencial por Codex o Gemini siempre que ambos respeten este protocolo.

Antes de empezar cualquier trabajo, el agente activo debe:

1. Leer el [protocolo de continuidad MultiIA](AI/PokeApp_Multi_AI_Continuity_Protocol.md) y este protocolo maestro.
2. Comprobar el estado real de Git.
3. Leer `docs/project-checkpoint.md`.
4. Leer el contrato de la fase actual.
5. Leer el `live handoff` de la fase si existe.
6. Leer el último `completion report` relevante.
7. Verificar que lo escrito en documentos coincide con Git, migraciones y tests reales.
8. Solo entonces continuar desde el siguiente paso exacto.

**Si existe contradicción, manda la evidencia verificable del repositorio.** Git, migraciones realmente aplicadas, SQL, tests y datos remotos tienen prioridad sobre una explicación antigua de chat.

La [memoria compartida](AI/PokeApp_Multi_AI_Continuity_Protocol.md#shared-memory-map) define qué documento mantiene cada información. El maestro conserva reglas y roadmap; el [checkpoint](project-checkpoint.md) identifica la fase activa; su live handoff mantiene el estado operativo único. Los informes conservan evidencias fechadas, no copias del estado vivo.

El alcance de la instrucción actual del usuario prevalece: una revisión de contexto o una tarea exclusivamente documental no inicia desarrollo ni staging.

No volver a leer meses de historial por defecto. El objetivo de este manual es precisamente evitarlo.

---

# 1. Roles y autoridad

## 1.1 Product Owner

El usuario es el Product Owner. Decide:

- comportamiento del producto;
- experiencia de usuario;
- reglas de negocio ambiguas;
- prioridades;
- alcance;
- qué se conserva del legacy y qué cambia;
- cuándo una propuesta de producto queda aprobada.

No se le debe preguntar por decisiones técnicas normales que un buen ingeniero puede resolver sin alterar el producto.

Cuando haga falta una decisión real de producto, presentar pocas alternativas claras, explicar consecuencias y recomendar una, pero no inventar la decisión.

## 1.2 ChatGPT

ChatGPT actúa como:

- arquitecto;
- especificador;
- revisor de entregas;
- coordinador de roadmap;
- traductor de decisiones del Product Owner a contratos implementables;
- coordinador de handoffs Codex <-> Gemini.

Flujo habitual:

**ChatGPT prepara un prompt completo -> agente ejecutor trabaja -> Product Owner pega el informe -> ChatGPT revisa -> se prepara la siguiente tarea.**

## 1.3 Codex y Gemini

Codex, Gemini, Antigravity y cualquier IA que retome la ejecución son **instancias sucesivas del mismo desarrollador a efectos de continuidad**. Cada una conserva la responsabilidad completa y audita el trabajo previo; no se reparten tareas pendientes por nombre de modelo. Las capacidades se comprueban en cada sesión.

No existe "código de Codex" y "código de Gemini". Existe un solo proyecto, una sola historia Git y un solo conjunto de contratos.

El agente activo puede tomar decisiones técnicas internas siempre que:

- no cambie reglas de producto aprobadas;
- no reabra contratos cerrados sin evidencia;
- mantenga compatibilidad;
- respete seguridad, tests, migraciones, locks e historia.

## 1.4 Regla fundamental de alternancia

**Las IAs ejecutoras nunca trabajan simultáneamente sobre la misma fase/repositorio.**

El modelo de trabajo es secuencial:

**Codex -> checkpoint/handoff -> Gemini -> checkpoint/handoff -> Codex**, o al revés.

El repositorio y sus documentos son la memoria compartida.

---

# 2. Qué es PokeApp 2.0

PokeApp es una aplicación privada para gestionar una liga/ChampionsLocke de Pokémon entre varios jugadores.

La aplicación combina:

- entrenadores y perfiles;
- equipos Pokémon;
- PC/cajas;
- Team Lock;
- jornadas y combates;
- divisiones y clasificación;
- tienda y economía;
- robos/canjes/efectos;
- juicios y sanciones;
- Copa;
- Hall of Fame;
- saves;
- automatización física futura sobre el save;
- Launcher/Companion local.

PokeApp 2.0 no es solo una web nueva. El objetivo final incluye frontend, backend, datos, migración, Launcher/Companion y automatización segura.

---

# 3. Arquitectura objetivo

La arquitectura final prevista es:

- **Frontend:** React.
- **Hosting frontend:** Cloudflare.
- **Backend:** FastAPI.
- **Base de datos / Auth / Storage:** Supabase V2.
- **Runtime local de usuario:** un único PokeApp Launcher/Companion.
- **Parser de saves:** frontera tipada alrededor de PKHeX.
- **Automatización física futura:** PKHeX Core / componente equivalente interno controlado por el Launcher.

Hasta el cutover:

- Streamlit/V1 continúa siendo el runtime legacy.
- V1 no se destruye ni se reescribe incidentalmente.
- V2 sigue aislado hasta la migración/cutover.
- No introducir dual-write improvisado.

---

# 4. Las tres capas de verdad del producto

Esta separación es fundamental y no siempre puede deducirse solo leyendo código.

## 4.1 Estado real del save

Ejemplos:

- party;
- cajas;
- Pokémon;
- objetos;
- medallas;
- flags del juego.

Es lo que realmente existe físicamente en el save.

## 4.2 Estado competitivo de PokeApp

Ejemplos:

- Team Lock;
- sanciones;
- robos;
- elegibilidad;
- clasificación;
- decisiones de Liga;
- economía;
- operaciones pendientes.

No todo estado competitivo debe escribirse inmediatamente en el save.

## 4.3 Historia congelada

Ejemplos:

- jornadas cerradas;
- snapshots;
- movimientos oficiales;
- campeón/finalista;
- Hall;
- archivos de temporada;
- certificados de Copa.

**Cambios posteriores del save o de datos vivos nunca deben reescribir silenciosamente historia ya cerrada.**

Este principio tiene prioridad sobre la comodidad de implementación.

---

# 5. Principios de producto no negociables

1. La migración debe ser conservadora, no una reescritura innecesaria.
2. Legacy se conserva salvo evolución de producto aprobada.
3. Mutaciones críticas pasan por backend/RPC transaccional, no por escrituras directas del navegador.
4. `service_role` es exclusivamente server-side.
5. No hay fallback silencioso a SQLite en producción V2.
6. Los hechos históricos cerrados no se recalculan desde estado vivo.
7. No inventar identidades, campeones, sanciones o datos históricos cuando la evidencia es ambigua.
8. En caso de duda histórica: **fail closed / pending explícito** antes que fabricar una respuesta.
9. No hacer refactor masivo durante fases funcionales.
10. El refactor global se reserva para el final.

---

# 6. Estado y roadmap global

## 6.1 Dónde consultar el estado vigente

El [checkpoint](project-checkpoint.md) identifica la fase activa y el progreso global.
Para Phase 8L, consultar el [live handoff](work-in-progress/phase8l-live-handoff.md)
para Git, estado local/remoto y siguiente acción, y el
[informe de entrega](phase8l-completion-report.md) para evidencia técnica fechada.
Este protocolo no mantiene otra copia de esas observaciones.

Antecedente histórico de seguridad: 030 se desplegó en V2 mediante dos registros:

- `20260924102756` - `030_trials_sanctions_api`
- `20260924103256` - `030_trials_sanctions_acl_completion`

**No reaplicar ninguno.**

Ningún documento demuestra por sí mismo el estado remoto actual. Verificar el
proyecto y su historial antes de una operación remota; aplicar el criterio de
evidencia de la sección 25.3.

## 6.2 Roadmap macro

Completado hasta el último snapshot:

- Phase 0 - Base green.
- Phase 1 - Cierre visual Streamlit.
- Phase 2 - Freeze funcional.
- Phase 3 - Contratos de dominio.
- Phase 4 - Servicios puros.
- Phase 5 - Repositories/application.
- Phase 6 - Supabase V2 greenfield.
- Phase 6.1 - PostgreSQL real.
- Phase 7 - RLS/security.
- Phase 7.1 - Supabase real.
- Phase 7.2 - Storage Cloud compatibility.
- Phase 8 - APIs críticas en múltiples subfases.
- Phase 8K.1 - Juicios/sanciones.

Pendiente desde el snapshot:

- Phase 8L - Copa/certificación/Hall.
- pequeño cierre/inventario de Phase 8.
- Phase 9 - Parser boundary + base Launcher/Companion.
- Phase 10 - React + Cloudflare.
- Phase 11 - Migración V1 -> V2.
- Phase 12 - Shadow mode.
- Phase 13 - Staging con datos representativos/clonados seguros.
- Phase 14 - Performance.
- Phase 15 - Cutover.
- Launcher/Companion completo.
- automatización física segura con PKHeX.
- extras del Product Owner.
- polish visual/sonoro.
- refactor/cleanup final.
- QA y release hardening.

## 6.3 Regla del porcentaje

El porcentaje global debe ser **ponderado por el objetivo final completo**, no por número de fases terminadas.

Incluye:

- backend;
- frontend;
- migración;
- Launcher;
- automatización física;
- polish;
- refactor;
- QA/release.

Una auditoría solo documental normalmente **no aumenta el porcentaje**.

---

# 7. Decisiones de producto ya cerradas que no deben rediscutirse sin motivo

## 7.1 Temporadas / Liga

Contratos 026-029 están cerrados y deben preservarse.

Entre otras cosas:

- admin puede no participar;
- preparación DRAFT y activación con setup completo;
- roster inicial gestionado en DRAFT;
- configuración usada no se reescribe libremente;
- cierre final de jornada no termina automáticamente la temporada;
- finish y archive son operaciones explícitas;
- Hall de Liga se basa en snapshot oficial;
- discard de temporada es lógico, no destructivo;
- historia cerrada se preserva.

## 7.2 Juicios / sanciones

Discord es el lugar social donde los jugadores discuten y deciden.

PokeApp:

- no implementa votación interna autoritativa;
- registra manualmente el resultado acordado;
- permite que un participante elegible registre el veredicto;
- no requiere admin para registrar el acuerdo;
- aplica consecuencias mecánicas de forma transaccional;
- guarda revisiones y correcciones append-only.

Sanciones soportadas:

- Store Ban;
- reducción de monedas;
- reducción de puntos;
- nota de liberación de Pokémon;
- otra nota/aviso.

Liberar Pokémon sigue siendo solo nota en esta etapa; no tocar saves todavía.

Las correcciones no borran historia: compensan o superseden.

## 7.3 Copa

Alcance deliberadamente moderado.

La Copa se usa menos que la Liga. No convertirla en una plataforma profesional de torneos.

Objetivo:

- Swiss + Top Cut;
- eliminación;
- dobles;
- Bo3 donde corresponda;
- byes correctos;
- evitar rematches cuando sea razonable;
- correcciones seguras;
- descalificación de jugador/equipo;
- cancelación lógica;
- Copa post-Liga;
- campeón certificado;
- Cup Hall.

No miles de simulaciones ni fuzzing masivo. Un conjunto razonable de tests representativos es suficiente.

La Copa puede jugarse **después de terminar/archivar la Liga**. De hecho, ese es un uso habitual: dar otra oportunidad de ganar algo a quienes quedaron peor en Liga.

## 7.4 D8

La decisión sobre cierto progreso/bonus individual entre temporadas sigue diferida para una fase donde existan datos suficientes de saves/migración.

No decidirla por adelantado sin necesidad.

---

# 8. Launcher/Companion - decisiones de producto

Debe existir **una sola versión de Launcher**, con todas las capacidades del producto.

No crear ediciones Basic/Advanced.

Dirección aprobada:

- Windows primero;
- instalador `.exe` normal;
- descarga desde la web de PokeApp;
- auto-update;
- mismo login que PokeApp;
- detección automática del save cuando sea posible;
- si no se detecta, pedir carpeta/ubicación;
- backup automático antes de toda mutación física;
- parser/PKHeX interno, no expuesto como complejidad al usuario;
- sync automático y manual;
- estado visible de operaciones;
- automatización física posterior para objetos, rare candies, caps/mints, robos, revive, alta/baja de Pokémon, etc.

El usuario final no debería tener que entender GitHub, Electron/Tauri, PKHeX o detalles internos.

---

# 9. Dirección visual y UX oficial

Esta sección contiene decisiones que **no se pueden deducir del backend** y deben conservarse cuando llegue React/polish.

## 9.1 Personalidad general

La interfaz debe sentirse:

- oscura;
- premium;
- competitiva;
- claramente inspirada en el universo Pokémon;
- con personalidad propia;
- moderna pero no genérica;
- atractiva sin exceso de adornos.

No convertirla en algo infantil, chillón o lleno de efectos gratuitos.

Regla de diseño:

> Primero mostrar lo que el usuario quiere hacer; después, los datos que explican esa acción.

## 9.2 Color

Cada sección puede tener una tonalidad/acento propio, manteniendo una base oscura común.

Ejemplos de dirección, no valores hex obligatorios:

- Inicio: azul/cian.
- Liga: azul + acento cálido.
- Team Preview/Combate: violeta/azul hielo.
- Copa: morado/dorado discreto.
- Tienda: ámbar, turquesa o jade, algo más cálido.
- Entrenadores: azul/verde suave.
- Normativa: acero/cian técnico.
- Hall of Fame: negro/dorado/iridiscente muy controlado.
- Temporada admin: azul oscuro con colores funcionales claros.
- Juicios: gris azulado/carmesí serio.

El color debe orientar, no decorar porque sí.

Éxito, warning y peligro deben conservar significado global consistente.

## 9.3 Elementos clickables

Cards, tabs, botones y recuadros seleccionables deben verse atractivos e inequívocamente interactivos.

Usar de forma sutil:

- borde;
- contraste;
- leve elevación;
- glow ligero;
- hover;
- estado activo claro;
- transición rápida.

Evitar animaciones exageradas.

## 9.4 Sonidos

Añadir al final sonidos UI muy suaves y discretos.

Posibles usos:

- click importante;
- selección;
- confirmación;
- éxito;
- alerta/error;
- hover solo en elementos relevantes, no en cada píxel interactivo.

Debe existir opción para desactivar sonidos y, si es práctico, volumen UI.

No reproducir sonidos automáticamente solo por entrar en una pantalla.

Preferir sonidos originales/inspirados, no copiar assets oficiales protegidos.

## 9.5 Loadings

No diseñar la aplicación alrededor de loaders visibles.

La mayoría de pantallas deberían sentirse instantáneas.

Solo mostrar un estado de carga discreto cuando exista latencia real: red, upload, sync, operación larga, etc.

No introducir skeletons constantes si no aportan nada.

## 9.6 Responsive

Responsive **real**, no simplemente "que no se rompa".

Debe tener calidad en:

- PC;
- portátil;
- tablet horizontal/vertical;
- móvil.

Team Preview y Combate son especialmente importantes en tablet porque durante combates se consulta el equipo propio o rival desde otro dispositivo.

También deben estar bien cuidados en móvil:

- Liga;
- Entrenadores;
- Tienda.

En móvil no hace falta copiar píxel por píxel la composición de PC, pero sí mantener:

- la misma calidad;
- la misma información útil;
- legibilidad;
- navegación cómoda;
- botones táctiles correctos;
- sin scroll horizontal absurdo.

## 9.7 Menú lateral

Mantener sidebar como concepto, pero rediseñarlo para que tenga más personalidad.

Debe mejorar:

- iconos;
- selección activa;
- hover;
- jerarquía;
- acentos por sección;
- sensación premium.

No hacerlo enorme.

## 9.8 Tarjeta del entrenador

Debe seguir siendo compacta. No ocupar 1/4 de la pantalla.

Pero debe permitir apreciar mejor:

- avatar;
- nombre;
- mínima información útil;
- equipo actual en formato pequeño pero legible;
- 8 medallas de la región actual.

Medallas obtenidas: iluminadas.  
Medallas no obtenidas: oscurecidas.

## 9.9 Login

La base actual gusta, pero se percibe demasiado sosa.

Cuando se rediseñe:

- conservar limpieza;
- añadir personalidad visual;
- sin sobrecargar;
- el mecanismo de autenticación cambiará con la nueva arquitectura.

## 9.10 Inicio

Actualmente contiene información útil mezclada con información secundaria y demasiada densidad.

Debe convertirse en un dashboard orientado a acción:

Prioridad visual:

1. próximo combate;
2. estado del equipo/Team Lock;
3. monedas/división/save relevante;
4. alertas importantes;
5. actividad secundaria después.

## 9.11 Liga

La base gusta y no debe reinventarse.

Mejoras:

- jerarquía;
- colores por división/estado;
- clasificación más clara;
- top relevante destacado con moderación;
- lectura de jornada más rápida.

## 9.12 Team Preview / Combate

Son de las pantallas favoritas actuales.

**Tocar poco.**

Conservar:

- estructura;
- IVs/stats;
- barras;
- niveles;
- habilidades;
- movimientos;
- sensación competitiva.

Mejorar principalmente:

- compactar el equipo propio para poder ver más sin subir/bajar continuamente;
- responsive tablet/portátil;
- traducciones oficiales correctas de movimientos/habilidades cuando la fuente fiable lo permita.

## 9.13 Copa visual

Prioridad visual baja-media.

Debe verse correcta, clara y coherente con el resto, pero no gastar una fase entera en diseño de Copa.

## 9.14 Entrenadores / PC / cajas

La base actual gusta mucho.

Mantener el desplegable de cajas; encaja bien aquí.

Pulir:

- tamaño de algunos bloques;
- selección;
- hover;
- protagonismo del Pokémon activo.

Bug conocido a vigilar en nueva arquitectura:

**al pulsar actualmente un Pokémon de una caja, a veces se abre otra pestaña del navegador y obliga a iniciar sesión de nuevo antes de mostrar detalles.**

Este comportamiento no debe sobrevivir en React/Cloudflare/Launcher. Los detalles internos deben abrirse dentro de la misma aplicación salvo recurso externo intencionado.

## 9.15 Tienda

Debe sentirse algo más como un PokéMart/bazar del mundo Pokémon y algo menos como un catálogo empresarial frío.

Objetivo:

- roleo ligero;
- tarjetas de producto bonitas;
- precios claros;
- categorías atractivas;
- tags/estado útiles;
- iluminación algo más cálida;
- sin perder claridad competitiva.

## 9.16 Saves

La pestaña legacy actual es demasiado verbosa para una acción simple.

Con Launcher/sync automático es probable que gran parte desaparezca del flujo web.

Si se conserva una pantalla de saves, debe ser muy simple y orientada a estado/sync, no a texto explicativo masivo.

## 9.17 Normativa

La dirección visual actual gusta bastante.

Conservar estructura y mejorar coherencia con el nuevo sistema visual sin rediseñarla innecesariamente.

## 9.18 Hall of Fame

Debe ser una pantalla especial.

Sensación:

- prestigio;
- legado;
- celebración;
- campeones destacados;
- dorado controlado;
- algo más de brillo/animación que el resto.

No convertirlo en estética de casino.

## 9.19 Temporada / panel admin

Es la pantalla que más necesita rediseño de UX.

Decisión aprobada: **Opción A - panel simplificado por áreas**.

Separar claramente:

1. Resumen.
2. Configurar temporada.
3. Gestionar entrenadores.
4. Gestionar competición.
5. Histórico.
6. Zona de riesgo.

Debe quedar obvio:

- qué está activo ahora;
- qué se está editando;
- qué cambiará al guardar;
- qué no cambiará;
- qué acción es reversible;
- qué acción es peligrosa.

Colores funcionales claros para editar/revisar/confirmar/peligro.

Las acciones destructivas o terminales deben estar separadas y explicadas.

## 9.20 Juicios

Estética más seria, tipo expediente/dossier.

Usar tono visual sobrio y formal. No parecer un formulario genérico ni una pantalla festiva.

---

# 10. Método de trabajo general del proyecto

## 10.1 Un objetivo por fase

Cada fase debe tener:

- objetivo claro;
- alcance explícito;
- fuera de alcance;
- criterios DONE;
- tests requeridos;
- migraciones esperadas;
- staging esperado;
- documentación de cierre.

No mezclar features de fases futuras "ya que estamos".

## 10.2 Desarrollo focalizado

Durante iteración:

1. inspección mínima necesaria;
2. implementación focalizada;
3. tests focalizados;
4. PostgreSQL focalizado si aplica;
5. corrección;
6. repetir solo lo afectado.

No ejecutar todo el universo de regresiones después de cada cambio pequeño.

## 10.3 Gate final

Cuando la implementación esté estable:

- suite completa;
- `compileall`;
- rebuild de migraciones;
- bootstrap generado;
- paridad de schema/grants/ownership;
- regresiones de contratos compartidos;
- concurrencia pertinente;
- rollback pertinente;
- seguridad;
- `git diff --check`.

Después:

- commit;
- push;
- staging;
- limpieza independiente;
- Advisor/security delta;
- documentación de cierre;
- commit/push documental.

---

# 11. Git - reglas permanentes

Trabajar normalmente en `main` según el flujo histórico del proyecto.

Nunca:

- force push;
- reescribir historia publicada;
- amend de commits ya publicados;
- rebase destructivo de `main` publicado;
- borrar cambios del usuario sin entenderlos;
- usar `git add -A` de forma despreocupada.

Preferir staging explícito de archivos.

Secuencia típica:

1. implementación + tests;
2. local green;
3. commit implementación;
4. push;
5. staging;
6. si hay bug solo de validator/harness: commit separado;
7. cierre documental;
8. commit/push docs;
9. `origin/main 0/0`.

Un cambio parcial solo se commitea si forma un checkpoint coherente y seguro. **No commitear código roto únicamente para facilitar un handoff.**

---

# 12. Migraciones - reglas permanentes

- Son append-only.
- No editar migraciones aplicadas.
- No reaplicar una migración porque un validator posterior haya fallado.
- El bootstrap se genera desde migraciones; no se parchea manualmente para hacer pasar una comparación.
- Antes de staging, confirmar historial remoto real.
- Aplicar únicamente la nueva migración comprometida y autorizada.

Si una migración se aplicó y luego falla el validador:

**registrar inmediatamente: "migración aplicada, validación pendiente".**

No confundir fallo del runner con fallo de despliegue.

---

# 13. Supabase V2 - reglas operativas

Proyecto V2 conocido:

`https://uwleqeuzsveqlugugzba.supabase.co`

Siempre verificar que la herramienta/credencial apunta al proyecto correcto antes de escribir.

Ha existido confusión histórica con otro proyecto, por lo que una URL/key vieja no basta como prueba.

Credenciales locales:

`.env.supabase-v2-rls.local`

Nunca imprimir ni versionar.

Staging:

- no bootstrap;
- no reset;
- no failure-injection DDL;
- no tocar V1;
- no usar datos reales como fixtures;
- no borrar real data para hacer pasar constraints.

Fixtures con prefijo único por fase, por ejemplo:

`phase8l_validation_<uuid>`

Obtener siempre un baseline fresco antes de cada validación remota importante.

Después del runner, hacer **limpieza independiente**, no confiar solo en que el propio script diga que limpió.

Comprobar según aplique:

- todas las tablas públicas;
- Auth users;
- identities;
- sessions;
- refresh_tokens;
- Storage objects;
- buckets;
- hashes/conteos de datos reales preexistentes.

---

# 14. Security / RLS

Reglas permanentes:

- `service_role` solo server-side.
- navegador, React y Launcher no reciben `service_role`.
- actor deriva de JWT verificado, nunca de un `trainer_id` arbitrario del body.
- funciones críticas deben revalidar actor, scope, estado y fuentes.
- RPCs críticas normalmente service-only.
- revisar grants de tabla y columna.
- revisar `TRUNCATE`, no solo INSERT/UPDATE/DELETE.
- revisar EXECUTE de funciones.
- revisar views escribibles/alternativas.
- `search_path` fijo donde corresponda.

Baseline conocido tras 8K.1:

- 24 ERROR;
- 4 WARN;
- 5 INFO.

Los 24 ERROR históricos corresponden a vistas 018 `security_definer_view` conocidas.

No arreglarlas incidentalmente durante una fase ajena solo para bajar el contador.

Comparar Advisor por:

- objeto;
- hallazgo;
- severidad;

no solo por número total.

Un INFO nuevo backend-only puede ser aceptable si el objeto está realmente inaccesible a browser roles y se documenta.

---

# 15. Idempotencia, CAS, locks y transacciones

## 15.1 Idempotencia

Misma identidad + mismo scope + misma key + mismo cuerpo semántico:

-> devolver receipt original estable.

No repetir efectos.
No incrementar revisión otra vez.
No regenerar sorteos.
No duplicar ledger/Hall/eventos.

Misma key con cuerpo semánticamente distinto:

-> conflicto explícito.

## 15.2 CAS

Un `expected_revision` obsoleto produce conflicto.

No actualizar automáticamente la revisión y reintentar a escondidas.

## 15.3 Locks

Respetar el orden de locks ya establecido por contratos compartidos.

Patrón general:

principal
-> advisory/receipt
-> season
-> participantes ordenados
-> jornada/dependencias
-> agregado específico
-> efectos/historia
-> evento/receipt

El orden exacto depende de la RPC existente. Inspeccionarla antes de tocarla.

No sustituir locks SQL por mutex Python.

## 15.4 Atomicidad

Una operación de negocio con varios efectos se ejecuta en una única transacción cuando el contrato lo exige.

No encadenar HTTPs como si fueran atómicos.

---

# 16. Concurrencia y rollback

Las carreras críticas deben probarse con:

- conexiones separadas;
- JWT/clientes separados;
- transporte independiente;
- PostgreSQL real cuando la semántica depende de locks.

No usar un cliente mutable compartido y después interpretar el resultado como carrera real.

Rollback local:

- inyectar fallo después de puntos de escritura importantes;
- comparar estado completo pre/post;
- no limitarse a conteos;
- incluir revisiones, ledger, eventos y artefactos.

Failure injection intrusivo se queda local. No crear triggers temporales destructivos en staging.

---

# 17. Tests - filosofía

Los tests existen para demostrar contrato, no para satisfacer un número.

Durante desarrollo:

- focalizados;
- rápidos;
- relacionados con el cambio.

Antes de DONE:

- suite global;
- regresiones compartidas;
- SQL real;
- concurrencia/rollback relevantes;
- seguridad;
- rebuild/paridad.

No bajar asserts para acomodar un bug.

No modificar producto para satisfacer una expectativa errónea del validator.

---

# 18. Distinguir bug de producto y bug de harness

Regla clave del proyecto.

Ejemplos históricos:

## 18.1 DTO inválido

Síntoma: 422 en vez del conflicto esperado.  
Causa: validator envió `results: []`, inválido por DTO.  
Respuesta correcta: arreglar fixture/request.  
No cambiar DTO ni guard de producto.

## 18.2 RLS devuelve éxito vacío

Una escritura filtrada por RLS puede devolver 200 con `[]`, no 403.

Verificar filas afectadas y estado final.

No aflojar policies solo para conseguir un status HTTP concreto.

## 18.3 RPC 404 por helper incorrecto

No reinterpretar una función válida como ausente sin comprobar el path real `/rpc/{name}`.

## 18.4 Cliente compartido en concurrencia

No concluir que faltan locks SQL cuando el test está mezclando auth/client state.

## 18.5 Bootstrap desfasado

Regenerar bootstrap desde migrations. No modificar migraciones históricas para hacer coincidir expectativas.

---

# 19. Entorno local conocido

Repositorio histórico:

`C:\Users\Antonio\Desktop\AntoPKMN\PokeApp`

Runner preferido:

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
```

Soporta `--pattern`.

Usar este runner frente a `unittest` directo cuando sea posible porque aísla:

- SQLite temporal;
- credenciales/Discord;
- `streamlit.secrets`.

Compile:

```powershell
py -m compileall -q .
```

Bootstrap:

```powershell
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
```

PostgreSQL portable histórico usado:

`$env:TEMP\pokeapp_pg17_phase8c_20260922\portable\pgsql\bin`

Puerto histórico: `55439`.

**Verificar existencia/puerto antes de reutilizarlo.** El nombre de una carpeta/base vieja no demuestra qué schema contiene.

Warnings conocidos que no se arreglan incidentalmente:

- Streamlit fuera de runtime;
- TestClient/httpx;
- LF/CRLF.

En PowerShell:

- entrecomillar rutas;
- comprobar `$LASTEXITCODE`;
- no interpretar `NativeCommandError` de warnings como fallo sin verificar resultado real.

Con `rg`, usar filtros `-g` apropiados en lugar de wildcards de ruta problemáticos.

---

# 20. Comparación de schema

Cuando aplique:

- `pg_dump --schema-only`;
- ordenar/normalizar según herramientas del proyecto;
- comparar schema, grants y ownership;
- normalizar solo tokens aleatorios `\restrict` / `\unrestrict` cuando sea necesario.

No excluir diferencias reales para conseguir un PASS.

---

# 21. Archivo protegido

Archivo local deliberadamente no versionado:

`docs/pokeapp-guia-completa-pestanas-y-producto.md`

Históricamente se ha preservado sin leer/modificar/stagear/borrar.

No tocar salvo autorización expresa.

Hash de referencia conocido:

`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`

Tampoco versionar:

- `.env.supabase-v2-rls.local`;
- `.streamlit/secrets.toml`;
- entornos virtuales;
- saves locales;
- artefactos temporales;
- credenciales.

---

# 22. Método de trabajo con IA - principio central

El proyecto **no pertenece a un chat**.

La información se divide en tres niveles:

## Nivel A - Duradero

Debe vivir en el repo:

- contratos de fase;
- `project-checkpoint`;
- migrations;
- tests;
- completion reports;
- live handoff mientras una fase está activa.

## Nivel B - Operativo

Puede vivir en el chat de fase, pero debe duplicarse en el live handoff cuando sea importante:

- problema descubierto;
- hipótesis;
- tests ejecutados;
- fallo pendiente;
- próximo paso.

## Nivel C - Conversación efímera

Comentarios, brainstorming y detalles que no cambian contrato.

Nunca dejar una decisión crítica únicamente en Nivel C.

---

# 23. Live Handoff obligatorio por fase

Cada fase activa debe mantener un fichero:

`docs/work-in-progress/phase<id>-live-handoff.md`

Ejemplos:

- `phase8l-live-handoff.md`
- `phase9-live-handoff.md`

No esperar al final de la fase.

Actualizarlo **durante** el trabajo.

## 23.1 Cuándo actualizar

Como mínimo después de:

- terminar un endpoint/conjunto coherente;
- terminar una parte importante de SQL;
- crear una migración;
- pasar un grupo de tests;
- descubrir un bug/gotcha importante;
- resolver un bug no obvio;
- hacer commit;
- hacer push;
- antes de tocar staging;
- inmediatamente después de aplicar migración remota;
- después de una validación remota;
- después de cleanup;
- cuando quede poca cuota/tiempo.

## 23.2 También informar en el chat

El agente debe dejar mensajes de progreso breves en el chat de la fase.

Pero el chat **no es la única memoria**.

Todo lo necesario para que otro agente continúe debe existir en `live-handoff.md`.

---

# 24. Plantilla obligatoria de Live Handoff

```text
# PHASE <ID> - LIVE HANDOFF

STATUS
IN PROGRESS / BLOCKED / READY FOR STAGING / DONE

LAST UPDATED
<timestamp local>

MEMORY REFERENCES
<protocolo canónico / checkpoint / contrato / informe de evidencia>

CURRENT GIT
branch:
HEAD:
origin divergence:
tracked tree:
untracked expected:

CURRENT OBJECTIVE
<qué se está intentando cerrar>

COMPLETED
- ...

VALIDATED
- fecha / commit / diff relevante / entorno / comando / resultado y exit code / evidencia
- distinguir VERIFIED, HISTORICAL/REPORTED y UNKNOWN
- ...

NOT YET VALIDATED
- ...

MIGRATIONS
- next migration:
- created: YES/NO
- committed: YES/NO
- pushed: YES/NO
- applied local: YES/NO
- applied staging: YES/NO/UNKNOWN, con fecha y evidencia
- exact remote version(s), if any:
- DO NOT REAPPLY:

STAGING STATE
- STAGING_UNVERIFIED hasta confirmar un estado de la sección 27
- exact project verified:
- fixture prefix:
- cleanup status:

ACTIVE / INTERRUPTED OPERATIONS
- proceso/PID o run ID, operación, fixture prefix, último resultado confirmado
- NONE verificado / UNKNOWN si no se ha inspeccionado

FILES / AREAS CHANGED
- ...

PROBLEMS FOUND
1. Symptom:
   Root cause:
   Fix/status:
   Remaining risk:

PRODUCT / CONTRACT DECISIONS USED
- ...

CURRENT UNCOMMITTED WORK
- NONE
or
- file: exact purpose/state

KNOWN FAILING TESTS
- NONE
or
- test + reason + whether product/harness issue

REMAINING
1. ...
2. ...

NEXT EXACT STEP
1. open/read ...
2. run ...
3. implement ...

DO NOT DO
- do not reapply ...
- do not touch ...
- do not assume ...

HANDOFF CONFIDENCE
- what the next agent should independently verify first
```

---

# 25. Cambio Codex <-> Gemini

## 25.1 Antes de cambiar de agente

El agente saliente debe:

1. terminar el bloque actual si es seguro;
2. actualizar live handoff;
3. ejecutar tests focalizados del bloque si procede;
4. dejar Git en estado entendible;
5. commit/push si existe un checkpoint coherente y seguro;
6. no hacer un commit roto solo para "guardar";
7. especificar cualquier cambio uncommitted;
8. especificar exactamente el estado de migraciones/staging;
9. escribir `NEXT EXACT STEP`.

## 25.2 Al entrar el nuevo agente

Debe:

1. comprobar `git status`;
2. comprobar branch/HEAD/upstream;
3. leer `project-checkpoint`;
4. leer contrato de fase;
5. leer live handoff completo;
6. revisar el último commit relevante;
7. comprobar migraciones locales y, si va a tocar remoto, las remotas;
8. confirmar que no está repitiendo algo ya hecho;
9. continuar desde `NEXT EXACT STEP`.

## 25.3 Si Git contradice el handoff

No adivinar.

Parar la implementación y reconciliar evidencia.

Usar el [criterio único de evidencia](AI/PokeApp_Multi_AI_Continuity_Protocol.md#documentation-rules):

- Contenido y publicación: archivos reales, diff, commits y referencias remotas.
- Comportamiento implementado: código y tests reproducibles ligados a esa fuente y entorno.
- Despliegue: proyecto identificado, historial remoto, schema, grants y validación real.
- Comportamiento deseado y alcance: instrucción vigente del usuario y contrato aprobado.

La evidencia directa y fechada prevalece sobre informes/chat antiguos para hechos
observados. Un commit no prueba un despliegue, y un bug no modifica un contrato
aprobado. Si no se puede comprobar un dato, registrar UNKNOWN; no inventar PASS.

---

# 26. Qué hacer si se agota cuota a mitad de prompt

Esta es una situación esperada, no un accidente excepcional.

## 26.1 Regla

**La fase no necesita terminar con el mismo agente que la empezó.**

## 26.2 Si queda poca cuota

No iniciar una operación remota grande solo por intentar "llegar".

Priorizar:

1. estabilizar el bloque actual;
2. actualizar live handoff;
3. guardar evidencia de tests;
4. dejar próximo paso exacto;
5. hacer commit/push si el checkpoint es coherente;
6. parar.

## 26.3 Si se corta de forma abrupta

El agente siguiente debe asumir que cualquier acción no evidenciada puede no haberse completado.

Comprobar antes de repetir:

- Git;
- archivo modificado;
- migración local;
- migration history remoto;
- tablas/funciones esperadas;
- logs si existen.

Especialmente:

**nunca reaplicar una migración porque no haya mensaje final del agente anterior.**

Primero verificar si ya está aplicada.

---

# 27. Protocolo de staging al alternar agentes

Staging es el punto más peligroso de un handoff.

Si el estado remoto no se ha verificado, registrar `STAGING_UNVERIFIED` y conservar
por separado el último estado histórico reportado, con fecha y fuente. No equivale
a `STAGING_UNTOUCHED` ni autoriza aplicar la migración.

Cuando exista evidencia suficiente, el live handoff debe distinguir exactamente uno de estos estados:

1. `STAGING_UNTOUCHED`
2. `STAGING_PREFLIGHT_COMPLETE`
3. `MIGRATION_APPLIED_VALIDATION_PENDING`
4. `VALIDATION_PARTIAL`
5. `VALIDATION_PASS_CLEANUP_PENDING`
6. `STAGING_DONE_ZERO_RESIDUE`

No usar frases ambiguas como "staging casi hecho".

Si el estado es `MIGRATION_APPLIED_VALIDATION_PENDING`, el siguiente agente:

- NO reaplica la migración;
- valida el schema/function real;
- corrige harness si hace falta;
- continúa validación.

---

# 28. Completion Report obligatorio

Cuando una fase está DONE, crear un informe durable.

Plantilla mínima:

```text
=== POKEAPP PHASE <ID> ===

RESULT

START / END / GIT

PRODUCT CONTRACT

IMPLEMENTATION

MIGRATION(S)

LOCAL VALIDATION

CONCURRENCY

ROLLBACK

STAGING

SECURITY / ADVISOR

CLEANUP

KNOWN LIMITATIONS / OUT OF SCOPE

COMMITS / PUSH

PROTECTED ITEMS

PROGRESS BEFORE / AFTER

NEXT

=== END REPORT ===
```

Debe separar claramente:

- lo implementado;
- lo probado;
- lo validado remotamente;
- lo no desplegado;
- lo pendiente.

No decir "staging real PASS" si en realidad solo hubo mocks.

En este proyecto, "staging real" suele significar FastAPI vía TestClient con Auth/JWT/PostgREST reales, no necesariamente API públicamente desplegada.

---

# 29. Cierre del live handoff

Cuando exista completion report y checkpoint actualizado:

- marcar live handoff como `DONE / superseded` o eliminarlo en un commit de cierre;
- no dejar dos documentos contradictorios diciendo estados distintos.

El completion report y project checkpoint pasan a ser la referencia durable.

---

# 30. Eficiencia de cuota/tokens

La cuota es un recurso de proyecto.

Reglas:

- no releer todo el repo por defecto;
- leer mínimos documentos relevantes;
- usar tests focalizados durante iteración;
- no repetir full gates innecesariamente;
- no hacer auditorías gigantes si una comprobación corta resuelve la duda;
- no crear microfases arbitrarias;
- combinar trabajo coherente cuando sea seguro;
- no sacrificar seguridad de staging por ahorrar cuota;
- no gastar tokens perfeccionando visuales antes de React/polish;
- evitar refactor prematuro.

Alternar Codex/Gemini tiene como objetivo **eliminar días muertos de cuota**, no duplicar trabajo.

No se presupone que ambos tengan el mismo modelo interno ni produzcan el mismo estilo de código. Los contratos/tests son el árbitro común.

---

# 31. Cuándo preguntar al Product Owner

Preguntar solo si hay una decisión que cambie realmente el producto.

Ejemplos:

- quién puede hacer una acción;
- cuándo entra en vigor;
- si una historia puede corregirse;
- qué experiencia de usuario se desea;
- semántica ambigua de una feature.

No preguntar por:

- nombre interno de una función;
- qué índice SQL usar si es evidente;
- si usar una helper privada u otra;
- estructura técnica que no cambia comportamiento;
- detalles de tests ordinarios.

Si hay una opción claramente superior técnicamente y no cambia producto, implementarla y documentarla.

---

# 32. Scope freeze y extras

Hasta completar el roadmap principal:

- no introducir nuevas ideas grandes en mitad de una fase;
- anotar extras en backlog;
- cerrar primero migración/runtime/Launcher.

Después del roadmap:

1. extras del Product Owner;
2. visual/audio polish;
3. limpieza/refactor global;
4. QA/release hardening.

El refactor grande va **al final**, no antes.

---

# 33. Política de código y arquitectura

Preferir:

- código explícito;
- funciones pequeñas cuando ayude;
- contratos tipados;
- límites de dominio claros;
- errores estables;
- lógica crítica server-owned;
- SQL transaccional para invariantes multi-write;
- adapters/repositories coherentes con arquitectura actual.

Evitar:

- abstracciones futuristas sin uso;
- frameworks internos de propósito general para una sola feature;
- duplicar dominios existentes;
- "limpiar" módulos no relacionados durante una fase;
- introducir dependencias solo por estética.

---

# 34. Datos históricos e importación

Cuando V1/legacy tenga datos incompletos o contradictorios:

- conservarlos;
- clasificarlos como legacy/no certificados/pending cuando proceda;
- no inventar UUIDs semánticos;
- no deducir un campeón solo por un campo `finished`;
- no deducir un veredicto por una sanción existente;
- no asignar temporadas sin evidencia;
- no borrar incompatibilidades para que pase una constraint.

La migración de datos se hará en una fase específica, no "por comodidad" durante otra.

---

# 35. Discord

Discord existe en el flujo social del grupo, pero **no es una integración técnica actual**.

No implementar bot/webhook/parser de Discord salvo fase futura explícita.

En juicios:

- Discord = conversación y decisión humana;
- PokeApp = registro oficial y efectos mecánicos.

---

# 36. Traducciones Pokémon

En Team Preview/Combate, el Product Owner valora especialmente nombres correctos de movimientos y habilidades en español.

Cuando sea viable, usar traducciones fiables/oficiales disponibles para generaciones compatibles.

No inventar traducciones.

No bloquear fases críticas por un detalle cosmético de localización; se puede terminar en polish si hace falta.

---

# 37. Teaser y calendario

Objetivo de comunicación actualmente manejado:

**29 de octubre de 2026 - teaser de PokeApp 2.0.**

Es una fecha de planificación/comunicación, no una razón para romper contratos o saltarse QA.

Objetivo interno deseable: llegar antes y usar margen para polish/material del teaser.

Si aparece un problema serio, se resuelve correctamente en lugar de esconderlo para cumplir una fecha.

---

# 38. Qué debe hacer una IA al recibir una nueva fase

Orden recomendado:

1. Verificar repo.
2. Leer checkpoint.
3. Leer master protocol.
4. Leer contrato de fase.
5. Leer live handoff si existe.
6. Confirmar alcance y fuera de alcance.
7. Crear/actualizar live handoff al inicio.
8. Trabajar por bloques coherentes.
9. Actualizar handoff durante el trabajo.
10. Tests focalizados durante iteración.
11. Gate final una vez estable.
12. Commit/push implementación.
13. Preflight remoto.
14. Staging incremental.
15. Validación/cleanup/security.
16. Completion report.
17. Update checkpoint.
18. Commit/push docs.
19. `origin/main 0/0`.
20. No comenzar automáticamente la fase siguiente.

---

# 39. Prompt corto para arrancar un agente nuevo

Usar este bloque junto con este documento y la tarea de fase:

```text
Estás continuando PokeApp 2.0 como agente de ingeniería.

El documento "PokeApp 2.0 - Protocolo Maestro de Proyecto y Handoff Multi-IA"
es contrato operativo obligatorio.

Antes de modificar nada:

1. Comprueba Git real: branch, HEAD, upstream, status y untracked.
2. Lee docs/project-checkpoint.md.
3. Lee el contrato de la fase actual.
4. Lee docs/work-in-progress/<fase>-live-handoff.md si existe.
5. Lee el último completion report relevante.
6. Verifica que migraciones locales/remotas coinciden antes de cualquier write remoto.
7. Si hay contradicción, la evidencia real del repo/DB manda y debes explicarla antes de continuar.

No repitas trabajo ya completado.
No reabras contratos cerrados sin evidencia.
No empieces otra fase automáticamente.

Mantén actualizado el live handoff durante el trabajo, no solo al final.

Si la cuota/tiempo parece insuficiente para terminar, prioriza un checkpoint coherente,
tests focalizados y un handoff exacto. No sacrifiques seguridad para declarar DONE.

Responde al Product Owner en español.
```

---

# 40. Prompt de emergencia cuando queda poca cuota

```text
QUEDA POCA CUOTA / TIEMPO.

No empieces nuevas operaciones amplias.

1. Termina solo el bloque actual si es seguro.
2. Ejecuta los tests focalizados imprescindibles del bloque.
3. Actualiza inmediatamente el live handoff con:
   - HEAD/status,
   - qué está completado,
   - qué está validado,
   - qué NO está validado,
   - migraciones local/remoto,
   - staging exact state,
   - problemas conocidos,
   - uncommitted changes,
   - NEXT EXACT STEP.
4. Haz commit/push solo si el checkpoint es coherente y seguro.
5. No hagas un commit roto solo para dejar constancia.
6. No apliques una migración remota si el gate local aún no está verde.
7. No declares DONE si queda cualquier gate obligatorio pendiente.
8. Termina con un resumen corto que otro agente pueda contrastar contra el fichero.
```

---

# 41. Checklist de entrada para Gemini después de Codex

```text
HANDOFF CODEX -> GEMINI

- [ ] He leído el master protocol.
- [ ] He verificado Git real.
- [ ] He leído project-checkpoint.
- [ ] He leído contrato de fase.
- [ ] He leído live handoff completo.
- [ ] He comprobado si hay cambios uncommitted.
- [ ] He identificado el último commit realmente publicado.
- [ ] He comprobado migration state antes de escribir remoto.
- [ ] Sé exactamente qué NO debo repetir.
- [ ] Sé cuál es NEXT EXACT STEP.
- [ ] He confirmado que no hay otro agente trabajando simultáneamente.
```

La misma checklist se aplica Gemini -> Codex.

---

# 42. Checklist de salida de cualquier agente

```text
- [ ] Live handoff actualizado.
- [ ] Estado Git documentado.
- [ ] Tests ejecutados documentados con resultado real.
- [ ] Fallos pendientes documentados.
- [ ] Migraciones: creado/commit/push/local/staging claramente indicado.
- [ ] Staging state usa una etiqueta inequívoca.
- [ ] Si hubo fixture, cleanup state documentado.
- [ ] Ningún secreto en logs/docs.
- [ ] NEXT EXACT STEP escrito.
- [ ] No se afirma DONE si no se cumplió el gate.
```

---

# 43. Definición de DONE

Una fase solo está DONE cuando cumple su contrato específico y, cuando aplique:

- implementación completa;
- tests focalizados;
- suite global;
- compilación;
- PostgreSQL real;
- migraciones rebuild;
- bootstrap/paridad;
- concurrencia;
- rollback;
- seguridad;
- commit/push;
- staging real;
- cleanup independiente;
- Advisor delta;
- docs de cierre;
- checkpoint actualizado;
- origin 0/0;
- archivo protegido intacto.

Si una fase es docs-only, no inventar gates de staging que no correspondan.

---

# 44. Qué NO significa DONE

No significa:

- "el código parece correcto";
- "pasaron los tests focalizados";
- "la migración se aplicó";
- "el validator empezó";
- "el chat dice que acabó";
- "el agente cree que no hay más".

DONE es evidencia reproducible de los gates apropiados.

---

# 45. Cierre conceptual

PokeApp 2.0 debe poder sobrevivir a:

- cambio de modelo;
- cambio de chat;
- compactación de contexto;
- agotamiento de cuota;
- una fase que dura varios días;
- un bug de validator;
- una migración aplicada antes de terminar validación;
- un cambio de agente a mitad de fase.

La forma de conseguirlo es sencilla:

**el contrato vive en el repo, la evidencia vive en tests/Git/DB, y el live handoff mantiene la continuidad operativa.**

Ninguna IA debe necesitar "recordar" lo que hizo la anterior si el protocolo se ha seguido correctamente.

---

# 46. Regla final para todos los agentes

> Construye solo lo que está autorizado, conserva lo que ya está demostrado, registra lo que haces mientras lo haces, y deja el proyecto en un estado que otro agente pueda continuar sin adivinar nada.
