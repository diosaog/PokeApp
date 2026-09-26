# PokeApp: guia completa de producto, pantallas y preferencias de Antonio

Documento para dar contexto a una IA que nunca ha visto la aplicacion.
Preparado el 22 de septiembre de 2026 sobre el commit `de485f7`.

## 1. Como usar este documento

Lee este documento como contexto de producto y de colaboracion. No es una orden para implementar de golpe todas las ideas mencionadas. Antes de modificar la aplicacion, comprueba el checkpoint del repositorio y la fase autorizada.

Se distinguen tres cosas: lo que contiene el codigo actual, lo que Antonio ha pedido expresamente y lo que corresponde a una fase futura. No conviertas una preferencia en una funcionalidad que supuestamente ya existe.

La descripcion actual se ha contrastado con el codigo local y su CSS. En esta tarea no se ha abierto la aplicacion en un navegador ni se ha comprobado el despliegue remoto. Por tanto, describir un estilo implementado no significa certificar que se renderiza bien en todas las pantallas. Esa distincion importa especialmente por los fallos visuales que hubo antes.

El checkpoint mas reciente es [project-checkpoint.md](project-checkpoint.md). El documento [pokeapp-2.0-handover-chatgpt.md](pokeapp-2.0-handover-chatgpt.md) aporta historia, pero tiene apartados anteriores a Fase 8 y cifras antiguas. No debe prevalecer sobre el checkpoint actual.

## 2. Que es PokeApp y para que se utiliza realmente

PokeApp es una aplicacion privada para organizar un reto Pokemon competitivo entre un grupo de personas. El reto combina una aventura individual tipo Nuzlocke/ChampionsLocke con competiciones entre entrenadores, una economia compartida, reglas propias y seguimiento del progreso.

Cada participante juega a su juego Pokemon fuera de PokeApp. El juego produce un archivo de guardado o save. PokeApp lee ese archivo para mostrar el equipo, las cajas, medallas, movimientos y otros datos. Los combates tampoco se simulan dentro de esta web: la aplicacion prepara, registra y organiza la competicion.

El contexto social es importante: los participantes se conocen, tienen motes para sus Pokemon, hablan en Discord y coordinan el reto. La normativa incluye jugar en directo en Discord y avisar por WhatsApp. La app da una referencia comun para que resultados, compras, equipos fijados y sanciones no dependan solamente de mensajes sueltos.

Antonio, identificado como Anto dentro de la app, participa y administra. Necesita que un entrenador pueda consultar y actuar con facilidad, y que el organizador controle la temporada sin mezclar herramientas peligrosas con las pantallas normales.

La experiencia que se busca es la de una herramienta de competicion Pokemon con identidad propia: reconocible, agradable de consultar durante muchas sesiones y suficientemente precisa para que la informacion oficial sea fiable.

### Conceptos que alguien nuevo necesita entender

| Concepto | Significado en PokeApp |
| --- | --- |
| Entrenador | Participante del reto, con perfil, save, equipo y estado competitivo. |
| Save | Archivo del juego, normalmente `.sav` o `.dsv`, del que se extraen datos. |
| Equipo actual | Los Pokemon que lleva el entrenador en su equipo dentro del save que se esta leyendo, hasta seis. |
| PC / Cajas | Pokemon almacenados fuera del equipo. Cada caja se representa mediante 30 posiciones. |
| Caja de muertos | Ubicacion convencional para Pokemon debilitados que ya no se pueden usar segun las reglas. La convencion legacy es Caja 8, con adaptaciones si el juego tiene menos cajas. |
| Team Lock / equipo fijado | Copia del equipo de seis elegida expresamente para una jornada. Un save posterior no deberia cambiar esa copia. |
| Jornada / tramo | Bloque de competicion asociado al avance del reto. No equivale necesariamente a un dia del calendario. |
| Liga A / Liga B | Dos divisiones. Los jugadores compiten dentro de su division y hay movimientos entre jornadas. |
| Puntos | Medida de clasificacion competitiva. No son moneda gastable. |
| Monedas | Recurso de la tienda obtenido por progreso y resultados, con gastos y posibles sanciones. |
| Compra | Registro de haber adquirido un objeto o comodin. Puede seguir pendiente de uso. |
| Canje / redencion | Aplicacion de una compra a una accion concreta, por ejemplo elegir un Pokemon para blindarlo. |
| Flag | Marca persistente, por ejemplo robado o blindado. No equivale al estado competitivo del entrenador. |
| Snapshot de jornada | Registro de resultados, premios y datos relevantes al cerrar una jornada. Protege la historia frente a cambios posteriores. |
| Archivo de temporada | Registro congelado del cierre de una temporada, incluido su campeon y equipo publico. |

### Un recorrido realista

Un jugador guarda la partida, entra con su PIN, sube el save y lo marca como actual. En Entrenadores comprueba que se han leido bien equipo, cajas y progreso. Cuando corresponde competir, fija los seis Pokemon de su equipo. En Team Preview consulta rivales y movimientos. Los resultados se registran desde la gestion oficial de Liga; al cerrar una jornada se calculan clasificacion, recompensas y movimientos. El jugador puede comprar y usar comodines. Si hay una infraccion, Juicios registra el caso y las sanciones. Al terminar y archivar una temporada, Hall of Fame conserva sus campeones.

Son pasos conectados, pero no una automatizacion total: subir un save no significa fijar equipo; comprar no significa canjear; finalizar una temporada no significa descartarla.

## 3. Apariencia general y evolucion del estilo

### La referencia aportada por Antonio

Antonio aporto capturas de Pokemon Champions. Le interesaban especialmente la forma de las cajas, las fichas de equipo y el modo de presentar tipos, movimientos, objetos y estadisticas. Pidio una aproximacion muy fiel en esos elementos, no simplemente una web con colores de Pokemon.

Las referencias tenian paneles violetas, fondos claros, superficies semitransparentes, iconos oficiales, filas compactas y sprites protagonistas. Pero una primera traduccion de esa referencia dejo la app demasiado clara. Antonio dijo expresamente que molestaba a la vista. A partir de ahi la peticion fue conservar la identidad y la composicion de Champions con una base visual mas oscura.

### Aspecto descrito por el codigo actual

La app utiliza fondos casi negros y azul noche, paneles oscuros algo mas claros, bordes finos, texto principal blanco suave y texto secundario gris azulado. Los acentos suelen ser azul y cian; dorado para elementos destacados o de palmares; verde, ambar y rojo para estados. Los Pokemon, retratos, medallas, objetos y tipos aportan color real.

Hay tarjetas y paneles con esquinas redondeadas, sombras moderadas, detalles geometricos y varias capas CSS acumuladas. Conviven nombres y estilos heredados de fases Champions, Platinum/BW2 y posteriores. La intencion final es homogenea, pero esta acumulacion es deuda tecnica: un selector nuevo no garantiza que gane frente a un estilo anterior.

El aspecto oscuro actual es una evolucion respecto a las primeras capturas. No debe describirse como una copia visual exacta de los paneles lilas iniciales, ni usarse la referencia inicial para volver a una pagina deslumbrante.

### Criterios visuales expresos que hay que conservar

1. La informacion Pokemon debe parecer parte de una interfaz Pokemon, con recursos reconocibles y proporciones cuidadas.
2. Un sprite debe tener suficiente presencia. Antonio rechazo tanto los Pokemon diminutos como los recuadros enormes con mucho espacio vacio.
3. Los tipos deben usar los recursos reales que indico: icono abreviado cuando falta espacio, imagen completa con nombre cuando se necesita etiqueta.
4. La ficha de movimiento no debe encerrar la imagen del tipo en otro recuadro decorativo innecesario.
5. La caja debe leerse como una caja de Pokemon, con posiciones ordenadas y seleccion directa del Pokemon.
6. La vista publica del equipo debe ser compacta. La vista propia puede aportar informacion privada adicional.
7. Los movimientos pueden mostrar sus detalles al pulsar. No necesitan presentar toda la explicacion de entrada.
8. Los menus, desplegables, formularios de PIN, notificaciones y estados vacios tambien deben adoptar el estilo nuevo.
9. Hay que eliminar explicaciones que no ayudan a tomar una decision. Eso no autoriza a borrar reglas, avisos de error o consecuencias de una accion irreversible.
10. No reinventar las superficies que ya funcionan visualmente. Las peticiones posteriores fueron de acabado y homogeneizacion conservadora.

### Fallos visuales que provocaron correcciones reiteradas

Se llegaron a mostrar nombres tecnicos de iconos como `expand_more` o `arrow_right` en lugar del icono. Tambien aparecio una campana enorme que ocupaba la pantalla, sprites demasiado pequenos en la sidebar, tipos con simbolos genericos incorrectos, tarjetas de equipo gigantes, cajas convertidas en una lista vertical de enlaces y una Normativa con etiquetas pegadas al contenido.

Estos ejemplos explican por que Antonio insiste en ver cambios reales. No basta decir que se ha modificado el CSS: hay que comprobar la pantalla correcta, el selector activo y el resultado visible con datos reales.

## 4. Acceso, sidebar, notificaciones y cambio de PIN

Aunque no son pestanas independientes, determinan la experiencia de toda la app.

### Acceso

El usuario escoge un entrenador de una lista, ve su retrato y escribe su PIN. La identidad visual se centra en PokeApp y en el entrenador elegido. El formulario esta planteado como una entrada compacta sobre el fondo oscuro, con selector, campo de contrasena y boton de entrada.

No es actualmente un registro abierto al publico. El runtime legacy tiene un registro de usuarios conocido. Antonio pidio retirar textos como instrucciones redundantes de seleccionar perfil y confirmar PIN, y explicaciones generales sobre los retirados que ocupaban espacio en el login.

El PIN conserva una experiencia sencilla para este grupo. La seguridad V2 ya implementada es otra capa: el puente de identidad obtiene una sesion Supabase Auth y la relaciona con `trainers.auth_user_id`. Eso no implica que el login Streamlit ya utilice ese puente.

### Sidebar

Incluye marca PokeApp League, retrato del usuario, nombre, division/contexto, medallas, miniaturas del equipo, notificaciones, cambio de PIN, enlaces de navegacion y cierre de sesion.

Los grupos visibles son Competicion, Entrenador, Informacion y Admin. Su finalidad es ordenar la navegacion; el nombre de un grupo no concede ni demuestra permisos. Por ejemplo, Juicios esta colocado bajo Admin, pero sus reglas legacy no son las mismas que las de Temporada.

La peticion final de Antonio fue mantener la sidebar abierta, sin posibilidad de ocultarla. Antes se podia plegar y luego no recuperarse en su pantalla. El codigo contiene estilos para forzar su presencia y ocultar controles de plegado. En una futura adaptacion responsive habra que preservar el acceso y comprobar el ancho disponible, sin dar por aprobada una navegacion oculta por defecto.

Los seis Pokemon pequenos de la ficha lateral deben ser identificables. La miniatura sirve para reconocer el equipo de un vistazo, no para mostrar todos sus datos ni ocupar media pagina.

### Notificaciones

El desplegable muestra avisos con titulo, detalle cuando hace falta, momento y un indicador visual de importancia. Recoge contexto de save, equipo fijado, tienda y actividad. El contador se calcula a partir de las clases de aviso; no debe explicarse como un sistema completo de leido/no leido si no existe ese estado.

Inicio muestra una seleccion corta de actividad reciente. El panel de sidebar permite consultar mas contexto. Los iconos deben tener dimensiones limitadas y no dejar nombres tecnicos visibles.

### Cambiar PIN

Se abre desde la sidebar. Si ya hay PIN guardado, pide el actual; solicita uno nuevo de cuatro digitos; valida y guarda. Antonio senalo expresamente que este formulario conservaba arte antiguo y debia integrarse en el nuevo estilo.

El cambio de PIN legacy no debe confundirse con una gestion completa de credenciales V2. No hay que afirmar que ese formulario ya rota credenciales de Supabase porque exista el puente nuevo en otro modulo.

Fuentes: [auth.py](../app/interfaz/auth.py), [sidebar.py](../app/interfaz/sidebar.py), [notifications.py](../app/interfaz/notifications.py), [utils.py](../utils.py).

## 5. Inicio: situarse antes de hacer nada

### Para que entra alguien aqui

Inicio responde a preguntas inmediatas: que jornada estamos jugando, en que division estoy, con quien tengo un combate pendiente, si he fijado el equipo, que saldo tengo y si mi save esta disponible. Es la pantalla de orientacion al volver a la app.

### Que ve

Hay una cabecera de enfrentamiento con el entrenador, un VS y el rival o el estado de asignacion. Debajo aparecen dos accesos: Team Preview y Fijar equipo/Ver equipo. Siguen indicadores de jornada, equipo fijado y monedas; una segunda zona resume tienda/promociones, save y participantes de la division. Al final hay una lista breve de actividad reciente, limitada a tres entradas en este render.

El estilo tiene mas enfasis competitivo que un formulario: nombres destacados en el enfrentamiento, superficies oscuras, cifras faciles de leer y bloques pequenos de contexto. La composicion se adapta a menos columnas en pantallas estrechas.

### Como se comporta

El rival se busca primero entre los combates sin resolver del usuario. Si no hay, puede mostrar un resultado ya marcado. Si aun no hay calendario, toma un candidato de la division con la etiqueta de calendario por definir. Ese candidato no debe presentarse en otra implementacion como un emparejamiento oficial confirmado.

Los accesos llevan a las pestanas correspondientes. Fijar equipo desde Inicio es un acceso a Entrenadores; no congela el equipo directamente desde esa cabecera.

### Que no tiene y que se quiere preservar

No tiene un combate jugable, un calendario personal completo ni una administracion de temporada integrada. Tampoco necesita un texto promocional explicando la app a personas que ya son usuarias.

Una version futura debe mantener el contexto y las acciones frecuentes sin repetir todo Entrenadores o toda Liga. Un aviso de save ausente es util; una explicacion larga sobre que es el panel no lo es. La campana gigante y el ruido visual fueron errores, no recursos esteticos aprobados.

Ejemplo: Antonio acaba de subir un save, pero todavia no ha fijado el equipo. Inicio debe permitir identificar ambas situaciones como distintas y acceder a fijarlo sin recorrer varios menus.

Fuente: [home.py](../app/interfaz/home.py).

## 6. Entrenadores: perfil, progreso, equipo, cajas e inspector

Es una de las pantallas mas importantes y una de las mas revisadas por Antonio. Reune datos leidos del juego y datos oficiales de PokeApp. No es simplemente una lista de usuarios.

### Seleccion y cabecera del entrenador

Un selector permite consultar el propio perfil o el de otro participante. Al entrar con un usuario, la pagina intenta seleccionar su propio perfil. Al cambiar de entrenador se limpia la seleccion anterior de Pokemon para no dejar abierto un inspector que pertenece a otra persona.

La cabecera combina retrato, identidad y contexto competitivo con metricas. El perfil debe sentirse personal y Pokemon, pero ser compacto: retrato reconocible, nombre claro, estados y cifras ordenados. No se busca una portada enorme por cada entrenador.

Se distinguen perfiles activos y retirados. La pagina puede mantener informacion consultable de un retirado, y mostrar limitaciones para sus acciones. No hay que confundir estar retirado con haber sufrido un robo: lo primero es un estado competitivo; lo segundo, una marca independiente.

### Resumen e inventario

El resumen incluye monedas, puntos, muertos, medallas y revividos tras wipe. Se apoya en la lectura del save y en datos registrados por la app.

Hay dos controles legacy propios del entrenador activo que conviene no omitir al explicar la pagina: guardar el numero de revividos tras wipe y reclamar la recompensa denominada Liga Finalizada. Esta ultima da 12 monedas, se habilita con al menos ocho medallas y evita reclamarla otra vez mediante una marca guardada. No es una prueba automatica de haber derrotado al campeon, ni es el boton administrativo que cierra la temporada multijugador.

El inventario tiene pestanas Compras (tienda) y Comodines. Se pueden consultar objetos registrados. El uso de comodines desde esta pantalla se habilita en el perfil propio y para un usuario no retirado. Si se abre un canje, reutiliza el flujo de Tienda.

### Equipo actual

Muestra seis posiciones. Cada Pokemon tiene sprite, mote o nombre, especie si procede, nivel, tipos, genero/shiny cuando esta disponible y marcas como blindado o robado. Los huecos que faltan se representan como vacios.

El renderer actual utiliza seis columnas de Streamlit y un boton Ver detalles bajo cada Pokemon. Esto es un detalle de implementacion existente; no hay que decir que todo el equipo ya se inspecciona pulsando exclusivamente el sprite. La interaccion directa de toda la casilla esta implementada en las cajas.

Antonio rechazo un equipo actual donde las seis tarjetas eran excesivamente altas, los tipos ocupaban demasiado y aparecian grandes botones azules debajo. Quiere poder reconocer y comparar los seis Pokemon con menos altura y buena proporcion entre imagen y contenido. Reducir la tarjeta no significa hacer irreconocible el sprite.

### Fijar equipo para una jornada

En el perfil propio aparece el estado: sin fijar, fijado o fijado tarde, con jornada y fecha cuando existe. El boton toma el equipo actual y requiere exactamente seis Pokemon. Guarda la copia del equipo y referencias al save, y puede emitir un aviso de Discord.

En el legacy, la marca de tarde se calcula a partir del estado de liga activa. No debe inventarse un calendario de plazos distinto al migrar la operacion.

La decision de producto es explicita: el jugador elige fijar sus seis Pokemon actuales. No hay seleccion automatica desde cajas, autoajuste del equipo ni fijado automatico cada vez que cambia el archivo. La futura Fase 8C se ocupa de llevar esta operacion a V2 con permisos y validaciones de servidor.

### PC / Cajas

Hay selector de caja, nombre, contador de ocupacion y libres, barra de ocupacion y una cuadricula de 30 posiciones. La caja de muertos recibe un tratamiento diferencial. Las posiciones vacias se mantienen y se atenunan; seleccionar un Pokemon marca su casilla y actualiza el inspector.

El codigo actual genera casillas con numero de posicion, nivel, sprite, nombre/especie y tipos. La cuadricula de escritorio esta planteada con seis columnas y cambia en breakpoints mas estrechos. La seleccion se transmite mediante un parametro de la pagina y estado Streamlit.

La referencia historica de Antonio era aun mas limpia: casillas pequenas parecidas a Champions, con Pokemon protagonista, sin nombre permanente ni simbolo de ojo, y abrir la ficha al pulsar el propio Pokemon. La implementacion actual conserva metadatos visibles; no debe afirmarse que aquella preferencia esta satisfecha al milimetro.

El orden tiene significado. Debe conservar la posicion real de los Pokemon en la caja y sus huecos. Ordenarlos alfabeticamente o eliminar huecos para que parezca mas limpio puede mostrar una caja distinta a la del save. Una lista de enlaces verticales con nombres pegados a los niveles es el fallo mostrado en capturas, no una variante de diseno aceptable.

No hay aqui un editor para arrastrar Pokemon, reorganizar el save, liberar ejemplares o moverlos entre equipo y cajas. La seleccion es para consultar.

### Inspector de Pokemon

Al seleccionar un Pokemon aparece una ficha con identidad, tipos, objeto, sprite de mayor tamano, estadisticas y movimientos. La ficha propia incluye naturaleza, habilidad y descripcion, IVs y EVs. La composicion actual organiza estas partes en secciones; no debe confundirse con el diseno compacto de Team Preview.

El inspector tiene una rama publica distinta. Oculta el bloque competitivo privado y no muestra los IVs/EVs reales del rival. El codigo calcula las estadisticas publicas con valores sustitutos y naturaleza neutra; esos numeros no se deben interpretar como los valores reales de su save.

En Team Preview las barras propias representan IVs sobre 31. En el inspector tambien hay estadisticas y una barra de PS. Una implementacion futura debe mantener clara esa diferencia para no etiquetar cualquier barra como IV.

### Que no debe mezclarse aqui

La administracion de estados oficiales de todos los entrenadores pertenece a Temporada. La gestion completa de archivos corresponde a Saves. La lectura de un perfil ajeno no autoriza a usar sus comodines ni a fijar su equipo. Ver Pokemon no equivale a poder descargar su save.

Si falta el archivo o falla el lector, la pagina muestra un estado explicito. Existe una configuracion tecnica del bridge para el propietario cuando no se carga; es una necesidad del legacy, no la experiencia final deseada para los jugadores.

Fuentes: [page.py](../app/entrenadores/page.py), [summary.py](../app/entrenadores/summary.py), [boxes.py](../app/entrenadores/boxes.py), [team_grid.py](../app/ui/team_grid.py), [detail.py](../app/entrenadores/detail.py), [detail_render.py](../app/entrenadores/detail_render.py).

## 7. Team Preview: preparar y consultar enfrentamientos

### Para que sirve

Un entrenador necesita consultar con rapidez los Pokemon y ataques de otro jugador antes de combatir, y revisar su propio equipo con mas detalle. Otra persona del grupo puede querer comparar dos participantes para seguir su enfrentamiento. Son dos usos distintos que esta pestana separa.

No es un simulador de combate, ni un constructor de equipos, ni una calculadora de dano. La normativa del grupo impone ademas restricciones sobre practicar con equipos ajenos y herramientas de calculo externas a Showdown; no se deben anadir esas utilidades por asumir que todo producto Pokemon las necesita.

### Modo Espectador

Permite elegir Entrenador A y Entrenador B, evitando que ambos selectores apunten a la misma persona. Muestra el enfrentamiento, divisiones y balance de enfrentamientos directos disponible. Debajo presenta resumen competitivo y equipo de cada uno.

Sirve para comparar participantes. Visualmente se apoya en dos lados, tarjetas de resumen, retratos y miniaturas de equipo. No significa ver una retransmision en directo o recibir turnos del combate.

### Modo Combate

Se escoge un entrenador. Si es el usuario conectado, se muestra Tu equipo y la version privada. Si es otra persona, se muestra Rival y la version publica. Hay hasta seis fichas con huecos explicitos si faltan Pokemon.

Las fichas incluyen mote/especie, tipos, nivel, genero cuando existe, objeto equipado con imagen y movimientos. Cada movimiento se puede desplegar para ver tipo, categoria fisico/especial/estado, potencia, precision, PP y descripcion. Las habilidades propias tambien pueden desplegar una explicacion.

Para el propio equipo se muestran seis filas de IVs: PS, Ataque, Defensa, Ataque Especial, Defensa Especial y Velocidad. Cada fila combina simbolo, nombre, barra proporcional a 31 y numero. Incluye naturaleza y habilidad propia.

La rama publica actual omite ese bloque privado, incluida la habilidad que se renderiza en el bloque privado. La referencia visual de Champions aportada por Antonio si contenia una linea de habilidad publica. Es una diferencia que debe describirse: copiar la referencia estetica no autoriza por si solo a publicar otro campo.

### De donde sale el equipo mostrado

Para la jornada actual se busca primero el Team Lock. Si existe un equipo fijado, se muestra esa copia. Si no existe, el codigo recurre al equipo del save y lo presenta como sin fijar. Ese equipo es informativo, no una confirmacion oficial equivalente a un lock.

El equipo actual de Entrenadores puede cambiar al subir otro save. El Team Lock ya guardado sigue siendo una copia. Esta distincion debe ser evidente al usuario y conservarse durante la migracion.

### Peticion estetica concreta de Antonio

Para los perfiles ajenos, Antonio mostro una referencia con seis fichas compactas, en dos columnas, que combinaban Pokemon, tipos pequenos, imagen del objeto y cuatro ataques alineados sin grandes recuadros individuales. La informacion completa del ataque solo debia aparecer al pulsarlo.

Para su propio equipo queria una ficha inspirada en la ficha de Charizard de Champions: nombre, tipos debajo, simbolos de las estadisticas y barras, utilizando los IVs de PokeApp en lugar de copiar el sistema numerico del juego de referencia.

Tambien pidio sprites animados. El codigo ya solicita sprites animados a los helpers de Showdown para esta vista. Eso no garantiza que haya una animacion valida para toda forma y especie; hay que tratar ausencias o fallos de recurso sin romper el espacio reservado.

### Limites relevantes

El modo de lectura no permite fijar el equipo: esa accion vive en Entrenadores. No expone IVs o naturaleza del rival por el hecho de cambiar de modo. Tampoco debe entregar datos privados al navegador y confiar solamente en ocultarlos con CSS en la futura web.

La privacidad legacy se aplica en los renderers del servidor Streamlit. V2 ya tiene proyecciones publicas y privadas para proteger los datos en su propia base, pero esa seguridad no significa que esta pantalla legacy ya este conectada a V2.

Fuente: [matchup.py](../app/liga/matchup.py).

## 8. Tipos, objetos y movimientos: una decision transversal

Antonio rechazo iconos genericos inventados para los tipos y facilito WikiDex como referencia de los recursos que queria. Su indicacion fue concreta: usar el simbolo aislado en espacios pequenos y el recurso completo con simbolo y nombre cuando corresponde una etiqueta.

El codigo actual centraliza esta representacion en `app/ui/type_icons.py`. Usa archivos locales de `assets/types/`: variantes completas `*-full.png` y variantes de icono `*-icon.svg`, embebidas como datos. Por tanto, no todos los recursos compactos son PNG, aunque el objetivo visual pedido se expresara como utilizar las imagenes originales.

No hace falta inventar un simbolo distinto para cada pestana. Entrenadores, Team Preview y los detalles de ataques deben usar la misma familia. Cuando el recurso falta hay un fallback de texto; que exista ese fallback no significa que Antonio lo prefiera a la imagen real.

El objeto equipado se representa con su imagen y nombre cuando se puede resolver. Un nombre puede necesitar traduccion, pero la traduccion nunca debe cambiar el objeto al que hace referencia. Motes, especies, tipos, habilidades y ataques tienen papeles distintos y no deben aparecer concatenados.

En un ataque, tipo, clase, potencia, precision, PP y efecto son informacion necesaria. La peticion de limpiar texto inutil no se refiere a borrar esa informacion. Lo que se elimina es repeticion o envoltorios que dificultan verla.

Fuente: [type_icons.py](../app/ui/type_icons.py).

## 9. Liga y Tabla: competicion oficial y clasificacion

### Que consulta un entrenador

Esta pagina permite saber en que division esta cada participante, como va la jornada, quien ha ganado los cruces, como queda la tabla general y que ocurrio en jornadas cerradas. Cuando corresponde, muestra el podio final.

Su composicion utiliza cabecera de jornada/estado, bloques diferenciados de Liga A y B, filas de participantes, resultados y tablas. La jerarquia debe favorecer comparar nombres y cifras, no esconder la clasificacion dentro de grandes tarjetas decorativas.

### Formato actual

El formato runtime es A/B. La configuracion base es de diez participantes, cinco por division, cuatro jornadas y tres ascensos/descensos entre divisiones. Estos son valores por defecto: la configuracion versionada de temporada gobierna jugadores, tamanos, numero de jornadas, movimientos y recompensas.

Los enfrentamientos de liga son dentro de cada division. La normativa los describe como Bo1: un combate para resolver el cruce. El ranking de division ordena por victorias; un empate entre dos usa enfrentamiento directo si existe, y si no, orden por nombre. Para grupos de tres o mas empatados usa menos muertos y despues nombre. No se debe sustituir esa regla por otra que parezca mas habitual sin una decision de producto.

### Recompensas base por posicion global de jornada

| Posicion | Puntos | Monedas |
| --- | ---: | ---: |
| 1 | 9 | 15 |
| 2 | 8 | 14 |
| 3 | 7 | 12 |
| 4 | 6 | 11 |
| 5 | 5 | 10 |
| 6 | 5 | 11 |
| 7 | 4 | 9 |
| 8 | 3 | 8 |
| 9 | 2 | 6 |
| 10 | 1 | 4 |

La sexta posicion recibiendo mas monedas que la quinta no es una errata que una IA deba corregir por iniciativa propia: es la tabla configurada de base. La regla de premio de robo al ultimo de B tambien es configurable.

### Puntos y penalizaciones

Los puntos de liga se acumulan desde jornadas. La cuenta competitiva incorpora una penalizacion base de 0,2 por muerto computable y posibles reducciones de Juicios. El legacy incluye los revivir usados en ese computo para que sacar un Pokemon de la caja de muertos no borre el coste competitivo. Los revividos tras wipe aportan dos unidades al computo, equivalentes a 0,4 por cada uno.

Ejemplo didactico, no dato real de un jugador: 17 puntos base, cinco muertos computables y una sancion de un punto producen 15 puntos. No se debe aplicar de nuevo cada jornada una penalizacion historica si el snapshot ya la incorpora segun el contrato existente.

### Jornada viva frente a jornada cerrada

Una jornada abierta admite la gestion autorizada de resultados. Al cerrarla se guarda un snapshot con clasificacion, premios, penalizaciones relevantes y configuracion. Cambiar mas tarde un save o las reglas de otra jornada no debe reescribir silenciosamente ese cierre.

Existe un flujo administrativo de correccion/recalculo de una jornada anterior. Debe distinguirse de recalcular el pasado al consultar la tabla: una correccion deliberada es una accion oficial, no un efecto de cargar una pagina.

### Quien modifica

La pagina normal esta orientada a consulta. Abrir jornadas, guardar resultados, modificar cierres, gestionar divisiones y reiniciar Liga se canaliza por la consola de Competicion en Temporada/Admin, con control de administrador. Poner botones distintos no sustituye validar permisos en la operacion.

No hay divisiones ilimitadas implementadas en el runtime actual. No hay arbitraje automatico de combates por leer el save. Copa mantiene su flujo separado y no debe mezclarse por defecto con las recompensas de esta tabla.

Fuentes: [ui.py](../app/liga/ui.py), [ranking.py](../app/liga/ranking.py), [league.py](../app/domain/services/league.py), [config.py](../app/season/config.py), [snapshots.py](../app/liga/snapshots.py).

## 10. Tienda: economia, compras, promociones y canjes

### Que significa comprar aqui

Se usan monedas de la competicion, no dinero real. El usuario compra recursos que forman parte del reto. No hay pagos bancarios, suscripciones comerciales ni un carrito de comercio electronico general.

La pantalla presenta cabecera, saldo y desglose, categorias de catalogo, compra pendiente de confirmar e historial. Cuando hay un canje iniciado, aparece el flujo para terminarlo.

El estilo debe permitir comparar objetos: imagen reconocible, nombre, precio, disponibilidad y accion. Los colores especiales de una promocion deben destacarla sin convertir todo el catalogo en una superficie brillante. Los controles de mantenimiento de flags no pertenecen al recorrido normal de compra.

### Categorias

| Categoria | Que contiene | Ejemplos actuales |
| --- | --- | --- |
| Comodines | Acciones especiales del reto | Revivir Pokemon 12, Robar Pokemon 12, Blindar Pokemon 12, Captura Extra 5 y Fosil 5 monedas. |
| Bayas | Objetos de recuperacion, curacion o combate | Varias bayas con imagen, efecto y precio propio. |
| Competitivos | Objetos equipados para combatir | Restos, Vidasfera, Mineral Evolutivo, objetos de eleccion y otros recursos del catalogo. |
| Crianza | Mejoras y recursos relacionados | Capsula Habilidad, Chapa Dorada, Chapa Plateada, Menta de Naturaleza y Objeto Evolutivo. |

Los nombres y descripciones del catalogo son datos que se deben comprobar al modificarlo. Esta guia describe las categorias y mecanismos; no certifica la exactitud de cada traduccion o efecto Pokemon del catalogo legacy.

### Como se obtiene y calcula el saldo

La implementacion actual combina monedas de Liga, cuatro monedas por medalla y el bonus de doce monedas por la reclamacion Liga Finalizada. Resta compras y sanciones de monedas. El saldo gastable no baja de cero.

Un bloqueo de tienda fuerza el saldo utilizable a cero mientras corresponde; eso no debe explicarse como si necesariamente se hubieran borrado todas las monedas historicas. Los retirados reciben una vista de saldo no utilizable y acciones restringidas.

Ejemplo didactico: seis medallas aportan 24 monedas; si se han obtenido 26 de Liga, gastado 12 y hay una reduccion de cuatro, quedan 34, sin bonus de finalizacion. Los puntos de clasificacion no entran en esa suma.

En V2 la fuente prevista es `coin_transactions`, un registro de movimientos. Esa tabla ya existe, pero el runtime Streamlit sigue usando la composicion legacy. No hay que describir el saldo actual como si ya procediera del ledger nuevo.

### Flujo de compra

El usuario escoge un articulo y se prepara una compra. La confirmacion vuelve a comprobar condiciones como saldo, bloqueo y promocion. Se registra la compra, se actualizan caches y pueden generarse actividad y aviso de Discord.

Una compra puede quedar pendiente de uso. Un premio gratuito tambien puede aparecer como registro a precio cero. El historial global distingue origen Premio/Compra, jugador, objeto, precio, fecha y estado. En esta pantalla se consultan hasta cincuenta registros recientes mediante el flujo actual.

La visibilidad global de compras es un comportamiento legacy real. En V2 compras, canjes y movimientos detallados tienen restricciones owner/admin. La futura API/UI debe resolver esa diferencia de forma explicita; no basta copiar el historial global y asumir que respeta el contrato privado.

### Promociones

Hay rebajas con calendario, estados, stock y reclamacion. La programacion legacy incluye una demora de apertura de 24 horas y referencias horarias de Madrid. Una promocion anunciada no es necesariamente comprable; puede estar pendiente de apertura o agotada.

Al migrar importa que dos compradores no puedan consumir la misma ultima unidad o conseguir un descuento ya caducado por tener una pagina antigua abierta. Eso requiere una operacion atomica del servidor. No hay que prometer que una interfaz React por si sola resuelve esa concurrencia.

### Que hacen los canjes de comodines

Robar permite elegir entrenador objetivo, origen en equipo/caja y Pokemon concreto. Comprueba restricciones, registra la redencion y marcas de robo/blindaje, consume la compra y puede conceder el comodin de blindaje asociado. El flujo actual indica expresamente que registra el robo sin modificar el save.

Revivir permite elegir un Pokemon de la caja de muertos, registra el uso, lo marca como revivido/blindado y conserva sus consecuencias competitivas. Tambien registra el efecto sin modificar fisicamente el save desde este flujo.

Blindar registra una proteccion sobre el Pokemon elegido. Captura Extra y Fosil representan permisos/recursos del reto; no son prueba de que la web haya escrito un encuentro o un fosil dentro de la partida.

Comprar, consumir una compra, aplicar una marca oficial y escribir bytes en un save son cuatro operaciones distintas. Confundirlas lleva a prometer automatismos que no existen.

### Que quiere Antonio respecto a la automatizacion

La futura importacion automatica de un Pokemon robado y el relleno de Caramelos Raros son utilidades concretas. Antonio ha excluido expresamente convertir todas las compras y canjes en ediciones automaticas del save. No ampliar el Companion a un editor universal de tienda por iniciativa de la IA.

Fuentes: [ui.py](../app/tienda/ui.py), [sections.py](../app/tienda/sections.py), [money.py](../app/tienda/money.py), [catalog_data.py](../app/tienda/catalog_data.py), [discounts.py](../app/tienda/discounts.py), [redeem.py](../app/tienda/redeem.py).

## 11. Saves: gestionar el archivo que alimenta la app

### Que ve el usuario

Una cabecera contextual, resumen de sus guardados, bloque de save actual, formulario para subir otro archivo e historial. El actual debe reconocerse de inmediato. Los demas son registros anteriores con acciones de seleccion y descarga.

Visualmente debe parecer un gestor de guardados integrado en PokeApp: nombre y metadatos legibles, estado actual destacado y botones ordenados. No necesita mostrar rutas de servidor, JSON del parser o conceptos de base de datos al entrenador.

### Acciones actuales

El formulario acepta `.sav` y `.dsv`. Subir y marcar actual registra el archivo, selecciona su registro como activo, escribe la copia local necesaria para el lector y refresca caches/snapshot. Refrescar invalida caches; no busca automaticamente un archivo nuevo en el ordenador del jugador.

El historial consulta hasta veinte registros del usuario. Permite establecer otro como actual y preparar su descarga. El propietario puede descargar su archivo. En modo retirado se deshabilita subir y cambiar el actual, manteniendo la consulta y las descargas propias permitidas por esta pantalla.

### Efecto sobre otras pantallas

El save alimenta equipo, cajas, medallas y datos del perfil. Seleccionar uno anterior puede cambiar las lecturas vivas. Eso no deberia alterar el equipo ya fijado de una jornada ni los snapshots oficiales cerrados ni un Hall archivado.

Un archivo subido y un archivo parseado correctamente no son lo mismo. La app depende del bridge para extraer datos. Un error de lectura debe comunicarse, no sustituirse por datos inventados o un mensaje que sugiera que todo esta actualizado.

### Que falta respecto a la vision final

La web actual no conoce automaticamente la ruta del save en el ordenador del entrenador ni mantiene sincronizada su partida por instalar el wrapper Electron. Tampoco el boton Descargar sobreescribe por si solo el archivo que utiliza el emulador.

La ruta local persistente, las copias de seguridad y la lectura del archivo actual pertenecen al Companion futuro. En esa vision el jugador tiene un archivo activo en la misma ruta; las copias de seguridad son copias, no sucesivos archivos que tenga que escoger como nuevos activos cada vez que juega.

Fuentes: [saves.py](../saves.py), [saves_support.py](../app/saves_support.py), [conex_pkhex.py](../conex_pkhex.py).

## 12. Copa: tres formas de torneo separadas de Liga

### Para que existe

Copa organiza competiciones adicionales. Su resultado puede alimentar el palmares, pero su estado y sus rondas no son las jornadas de Liga A/B. En esta pestana existe un selector de formato y un contenido distinto para cada modalidad.

La apariencia utiliza identidad de torneo, indicadores de ronda y participantes, cruces, clasificaciones y tarjetas de equipos. Debe poder leerse quien compite contra quien y quien avanza. La decoracion no puede dificultar seguir el cuadro.

### Copa / formato suizo

Permite seleccionar participantes, crear la competicion, generar emparejamientos y registrar ganadores por ronda. Mantiene victorias, derrotas, descansos/byes, historial, clasificados y eliminados. Incluye Buchholz, una medida basada en los resultados de los rivales, y un top cut final para resolver el campeon.

Hay controles legacy de edicion manual de jugadores y emparejamientos, ademas de consulta de enfrentamientos/equipos disponibles. La implementacion contempla un top cut de cuatro, semifinales y final. No debe describirse simplemente como una eliminatoria directa.

### Torneo / eliminatoria Bo3

Se eligen participantes y se puede sortear el orden. Se genera un bracket, con pases libres cuando hacen falta para completar el cuadro. Cada enfrentamiento usa marcador de serie y ganador; Bo3 significa que gana quien consigue dos victorias.

Se registran o editan resultados, se cierra una ronda cuando estan completos y se avanza a la siguiente. El ultimo ganador se registra como campeon. Existen controles para limpiar resultados y reiniciar configuracion/torneo.

### Copa Dobles

Se forman equipos de exactamente dos entrenadores, con nombre y logo cuando hay un recurso correspondiente. Se validan nombres y participantes para evitar duplicados entre equipos.

El formato es una liga todos contra todos entre esas parejas, seguida de final entre las dos mejores cuando se completa la fase regular. Muestra equipos, rondas, resultados de series, tabla y final. El logo se resuelve desde recursos locales por nombre normalizado; no hay que prometer un editor de logos que no se ha implementado.

### Permisos y deuda que deben quedar claros

Copa sigue siendo un modulo legacy funcional con controles de configuracion, resultados y resets en su propia pagina. No se ha demostrado que todos esos controles tengan el mismo filtro administrativo que la consola de Liga. De hecho, los renderers revisados no aplican alli la barrera `admin_mode` de Liga.

Por eso no se puede decir que todo lo peligroso de la aplicacion ya se ha centralizado en Temporada. La centralizacion cubre el flujo oficial de temporada/Liga y mantenimiento trasladado; Copa necesita su propia matriz de permisos al migrar. Este documento registra la diferencia, no cambia su comportamiento.

No hay combates simulados ni lectura automatica de un resultado de Showdown. Los resultados se introducen en la app. Tampoco hay que inventar nuevos formatos porque exista un selector de modalidades.

Fuentes: [pages.py](../app/interfaz/pages.py), [swiss.py](../app/copa/swiss.py), [elim.py](../app/copa/elim.py), [doubles.py](../app/copa/doubles.py).

## 13. Juicios: expedientes, votacion y sanciones

### Que significa esta pestana

Juicios formaliza incidencias del reto: que se acusa, a quien, con que informacion, en que estado esta el caso, que decide el jurado y que consecuencias oficiales tiene. Se trata de una mecanica social del grupo, no de asesoramiento juridico.

La pagina muestra indicadores de expedientes, filtros, casos consultables y detalle del seleccionado. Utiliza etiquetas de estado y paneles de informacion para que el asunto, acusado, fechas y resolucion no se pierdan en texto corrido.

### Datos y recorrido

Un expediente incluye titulo, acusado, resumen, fecha prevista, pruebas, testigos, prioridad, categoria, visibilidad, tamano del jurado, notas y castigos propuestos. Se crea como Propuesto, puede pasar a En proceso y termina como Finalizado, con veredicto pendiente/culpable/no culpable segun el flujo.

Durante el proceso se registran votos culpable/no culpable. La mayoria puede finalizar automaticamente el expediente. Tambien hay controles de edicion de informacion, propuesta de castigos y cierre. El boton de cancelar un juicio en el legacy lo elimina permanentemente y reordena la numeracion, por lo que requiere confirmacion; no equivale simplemente a marcarlo archivado.

### Permisos reales del legacy

Los expedientes publicos son visibles a los usuarios que acceden a la app. Los privados quedan visibles para su creador segun el helper actual. Editar se autoriza por ser el creador del caso, no por una comprobacion general de `is_admin`.

El creador puede registrar votos en nombre de otros jurados. Otro usuario solo puede registrar el propio conforme a las comprobaciones del flujo. Que la opcion Juicios este bajo el grupo visual Admin no convierte automaticamente la pagina en exclusiva de Antonio.

Esta semantica debe trasladarse a una matriz explicita antes de crear endpoints. Una migracion que sustituya creador por administrador sin decision previa alteraria el producto; copiarla sin revisar identidad y permisos tambien seria insuficiente.

### Sanciones disponibles

Hay bloqueo de tienda/monedas utilizables, reduccion de monedas, reduccion de puntos, liberacion o muerte de un Pokemon y otros castigos descritos en texto. Las sanciones que tienen integracion economica o competitiva se consultan desde esos calculos; registrar que alguien debe liberar un Pokemon no prueba que se haya editado automaticamente su save.

Existen plantillas orientativas en el codigo: primera falta con un punto; reincidencia con doce monedas, dos puntos y bloqueo de tienda; grave con veinte monedas, cuatro puntos, bloqueo y liberacion de un Pokemon a concretar. Son plantillas del formulario, no un detector automatico de infracciones ni una sentencia que se imponga sin el flujo del expediente.

### Estilo y limites

La prioridad es distinguir propuesta, proceso y resolucion mediante estado, jerarquia y contraste. Debe conservar el lenguaje visual de PokeApp con un tono mas documental. No necesita copiar la apariencia de una tienda o de una ficha de Pokemon.

No hay deteccion automatica completa de trampas, analisis de streams o auditoria de cada accion del juego. Este modulo sigue guardando estado legacy y su integracion V2 completa esta pendiente.

Fuentes: [ui.py](../app/juicios/ui.py), [forms.py](../app/juicios/forms.py), [repo.py](../app/juicios/repo.py), [constants.py](../app/juicios/constants.py), [penalties.py](../app/juicios/penalties.py).

## 14. Normativa: manual de consulta del reto

### Que debe encontrar alguien

Normativa responde a dudas concretas: se puede capturar este Pokemon, cual es el siguiente cap, que objetos estan prohibidos, cuantos ascienden o que hace un comodin. Tiene que permitir localizar la respuesta y leerla con comodidad.

Se organiza en siete capitulos visibles: Normas Nuzlocke, Equipo Legal, Tramos Liga, Level Caps, Liga A/B, Comodines y Normas Generales. Dentro hay reglas y subapartados. Que el texto interno numere mas secciones no significa que haya mas pestanas principales.

### Contenido necesario

Nuzlocke cubre muerte permanente, primera captura de ruta, encuentro perdido y mote obligatorio. Incluye clausulas de duplicados, legendarios, shiny, fosiles, baneos y transferencias entre juegos.

Equipo Legal recoge limites como un pseudo-legendario y un legendario menor/singular de hasta 600 BST, junto con restricciones de duplicados. Tramos explica la relacion entre aventura y liga, Bo1, Copa Bo3 y clausulas de combate.

Level Caps contiene tablas de gimnasios y Liga Pokemon. En el contenido actual se encuentran Cheren 16, Hiedra 22, Camus 29, Camila 36, Yakon 40, Gerania 47, Lirio 58 y Ciprian 61; Alto Mando a 70 e Iris a 71. Son valores del reglamento de ese contexto de juego, no topes universales para cualquier generacion.

Liga A/B muestra divisiones, movimientos, puntos y monedas. Tramos y esa seccion se adaptan parcialmente a la configuracion vigente. No todo el reglamento se genera automaticamente desde un motor de reglas: las clausulas generales y los caps siguen teniendo contenido especifico en codigo.

Comodines explica revivir, robar, blindar, captura extra y fosil. Normas Generales recoge intercambios prohibidos, explotacion del juego, limites de compras especiales, practica, robos repetidos, conflictos/vacios legales y obligaciones de emision/aviso al grupo.

### La decision de diseno y por que hubo varias iteraciones

Antonio quiso un manual oficial de competicion: cabecera ordenada, indice documental, capitulos, articulos, tablas y notas relevantes. Una primera reescritura cambio el markup, pero dejo textos pegados, botones enormes para los capitulos, reglas como un bloque corrido y demasiado espacio vacio.

Su correccion fue precisa: habia que disenar la lectura. Los caps, puntos y monedas necesitan tablas con columnas alineadas. Los articulos necesitan separacion entre numero y texto. El indice debe parecer navegacion de documento; los avisos importantes deben destacarse. El fondo geometrico no debe ser mas protagonista que el contenido.

La implementacion actual utiliza ancho de lectura acotado, cabecera con metadatos y sello, indice y cuerpo de capitulo con superficies propias. El objetivo de esa composicion es consultar mejor, no anadir etiquetas de Manual oficial a texto sin estructura.

### Integracion y limites

El contenido tambien produce versiones de texto/secciones para la sincronizacion con Discord. Si se actualiza una regla, importa que lo publicado y lo consultado no diverjan.

La formula resumida de monedas en Normativa no enumera todo lo que hace el calculo legacy, como bonus y sanciones. Es una diferencia documental a tener presente: para explicar la economia completa hay que consultar tambien el codigo, no repetir solo esa frase.

No es un editor general de reglas, ni un sistema que impida automaticamente toda infraccion. La limpieza de sobreexplicaciones de la app no autoriza a recortar el contenido normativo necesario.

Fuentes: [normativa.py](../app/interfaz/normativa.py), [pages.py](../app/interfaz/pages.py).

## 15. Hall of Fame: conservar quienes ganaron y con que equipo

### Que se ve

Una cabecera de palmares con cifras de contexto y una vitrina de campeones. Las entradas identifican competicion, campeon, contexto/resultado disponible y equipo cuando existe. Puede incluir Liga, Copa suiza, eliminatoria y Dobles.

La identidad visual admite mas enfasis en reconocimiento: dorados, trofeos, retratos y sprites. Sigue necesitando legibilidad, proporciones contenidas y coherencia con la base oscura. No es otra tabla operativa ni una portada gigante con poca informacion.

### Que se ha protegido funcionalmente

Antes existia el riesgo de que el equipo de un campeon dependiera del save vivo: subir otra partida podia cambiar lo que parecia haber usado al ganar. El archivo de temporada guarda el snapshot publico del equipo y Hall prefiere las entradas archivadas.

Se combinan entradas guardadas, fuentes automaticas y archivos de temporada. Esa prioridad de archivo protege especialmente la historia de temporada; no hay que afirmar sin revisar cada flujo legacy que toda copa antigua posee el mismo grado de congelacion.

### Que no hace

No permite cambiar libremente ganadores ni publica IVs privados del campeon por el hecho de mostrar su equipo. Tampoco sustituye el detalle de jornadas de Liga. Si todavia no hay campeones, el estado vacio debe decirlo con claridad, sin fabricar entradas de ejemplo que parezcan oficiales.

Ejemplo: si Anto gana una temporada con un equipo y luego sube un save con seis Pokemon diferentes, el Hall de la temporada archivada debe conservar el equipo ganador.

Fuentes: [hall_of_fame.py](../app/interfaz/hall_of_fame.py), [archive.py](../app/season/archive.py).

## 16. Temporada / Admin: la gestion oficial

Esta pestana es exclusiva de Anto en el runtime legacy. Existe tanto filtro de navegacion como comprobacion al renderizar. V2 utiliza un rol administrativo explicito en `trainers.is_admin`; no debe perpetuarse un permiso por nombre en la futura API.

Visualmente es un panel de trabajo mas denso: resumen, tablas de configuracion, formularios, historial, estados y una zona de riesgo diferenciada. Mantiene el estilo nuevo, pero necesita advertencias operativas que no deben borrarse como supuesto texto sobrante.

### Estado

Muestra el ciclo de temporada y configuracion actual. Permite las transiciones autorizadas: finalizar, archivar y preparar la siguiente. Los estados de dominio son ACTIVE, FINISHED, ARCHIVED y DISCARDED.

Finalizar deja constancia del fin competitivo; archivar genera la memoria historica; preparar nueva temporada establece un nuevo contexto activo. Descartar tiene otro significado y no crea el mismo archivo ni Hall.

### Configuracion

Edita la configuracion versionada: participantes, jornadas, divisiones/tamanos compatibles con A/B, movimientos, tablas de puntos y monedas y reglas funcionales. Muestra diferencias y validaciones antes de guardar, junto con historial de versiones y una vista tecnica desplegable.

Las reglas incluyen equipo fijado obligatorio, premio de robo al ultimo de B y separacion de Copa. El objetivo es que las decisiones configurables tengan efecto real y una version identificable, sin recalcular a escondidas la historia cerrada.

### Entrenadores

Gestiona estados oficiales como activo, retirado, abandonado y descalificado, y marcas independientes como haber sido robado. Estas operaciones se centralizaron para no dispersarlas por los perfiles publicos.

Estado y marca no son intercambiables: marcar robado a alguien no deberia retirarlo de la competicion. Tampoco abandonar y ser descalificado son sinonimos que una migracion deba colapsar sin revisar sus efectos.

### Competicion

Permite abrir la consola oficial de Liga. Desde ella se gestionan jornadas, resultados, divisiones, cierres y correcciones. El mismo modulo de Liga se renderiza en modo administrativo, con permisos reforzados para mutaciones.

No significa que todas las opciones de Copa y Juicios ya esten contenidas aqui; esos modulos conservan sus propias rutas legacy.

### Historial

Lista archivos de temporadas con fecha, campeon, jugadores, jornadas y estado. Permite abrir un resumen. Incluye notas privadas de planificacion. Las notas no son contenido para todos los entrenadores ni instrucciones de implementar automaticamente una siguiente temporada.

### Riesgo

Incluye mantenimiento/reset de flags de Pokemon, por entrenador o global, con confirmacion explicita. Tambien permite descartar la temporada activa con advertencia de que no genera archivo historico ni Hall.

La presencia de esta zona no permite realizar resets durante una auditoria, una explicacion o una migracion tecnica. El contexto de una accion importa tanto como tener acceso al boton.

Fuente: [temporada.py](../app/interfaz/temporada.py).

## 17. Como se conectan las pantallas sin confundir sus datos

| Dato o accion | Donde nace o se gestiona | Donde se consulta despues |
| --- | --- | --- |
| Save actual | Saves y lector | Entrenadores, cajas, progreso, previews sin lock y partes de economia. |
| Equipo fijado | Accion propia en Entrenadores | Inicio, Team Preview, contexto de jornada y notificaciones. |
| Resultados oficiales de Liga | Temporada > Competicion | Liga, puntos/monedas y, al cierre correspondiente, historia/Hall. |
| Compra | Tienda | Saldo, historial e inventario. |
| Canje/flag | Tienda o flujo de comodin desde Entrenadores | Inventario, marcas del Pokemon y computos afectados. |
| Sancion | Juicios resuelto segun sus reglas | Puntos, saldo/tienda y avisos. |
| Cambio de reglas versionadas | Temporada > Configuracion | Liga, premios, validaciones y partes dinamicas de Normativa. |
| Archivo de temporada | Temporada > Estado | Historial y Hall sin depender del save vivo. |

Una pantalla no deberia convertirse en otra fuente independiente para el mismo dato oficial. En particular, el navegador no debe decidir premios, identidad o saldo simplemente porque puede mostrarlos.

### Visibilidad: lo publico es publico dentro de la app

Consultar el perfil publico de un entrenador no significa permitir acceso anonimo desde Internet a sus archivos. El contrato V2 limita el acceso anonimo y ofrece vistas de informacion segura para usuarios autenticados. Los saves raw, payloads completos y detalles privados tienen otro nivel de acceso.

Hay que mantener una matriz por operacion: quien puede consultar, quien puede modificar y si actua sobre si mismo, sobre un caso propio o como administrador. Los ejemplos de Copa, Juicios e historial de compras muestran que no basta deducirlo de donde esta el boton.

## 18. Discord: avisos del grupo, fuera de las pestanas

La integracion conocida como Aaron Avisa envia notificaciones mediante webhook. Hay avisos de compras, rebajas, equipos fijados, equipos pendientes, resultados, cierres de jornada, retiradas y cambios de Normativa, segun la configuracion y el flujo.

No debe confundirse con un bot conversacional completo que controla toda la app con comandos. El mecanismo principal documentado aqui son notificaciones con contenido estructurado y reintentos.

Durante trabajo interno de migracion no deben enviarse anuncios al grupo por defecto. Si el sistema esta silenciado, no hay que presentarlo como un fallo de negocio. A futuro los avisos de mutaciones criticas deben originarse desde operaciones de servidor/eventos, evitando depender de que alguien abra una pagina.

Fuente: [discord_notify.py](../app/discord_notify.py).

## 19. Estado tecnico actual y lo que sigue pendiente

### Lo cerrado segun el checkpoint

La base funcional y la referencia visual de Streamlit estan congeladas. Se implementaron snapshots, configuracion versionada, estados y flags de entrenador, ciclo de temporada, archivo, Hall estable y actividad. Se extrajeron contratos de dominio, servicios puros y repositorios.

Supabase V2 tiene migrations 001-018, bootstrap reproducible, tablas separadas por entidades, seguridad RLS, vistas y Storage privado `raw-saves`. Fases 7.1 y 7.2 figuran cerradas: el validador real de staging paso con `RESULT ok checks=13`, y la compatibilidad de policies de Storage Cloud fue corregida/aplicada.

Fase 8A.1 implemento el puente de PIN a Supabase Auth. Fase 8B incorporo el esqueleto FastAPI: `GET /health`, `POST /v1/auth/pin-login`, `POST /v1/auth/refresh` y `GET /v1/me`, con verificacion de identidad y limitacion de intentos. El checkpoint documenta 146 tests; no se han ejecutado de nuevo para redactar esta guia.

### Lo que eso no significa

La app de uso diario sigue siendo Streamlit con persistencia legacy/V1. Supabase V2 no es todavia su fuente operativa de verdad. No hay una web React desplegada por el hecho de haber creado tablas V2. La API de autenticacion tampoco implica que compras, locks, cierres o canjes ya pasen por ella.

V1 sigue existiendo. No hay autorizacion para borrarla, conectar Streamlit a V2 o empezar a escribir cada operacion en ambas bases. La coexistencia de V1 y V2 no define por si sola un dual-write correcto.

### Orden pendiente

1. Fase 8C: mutacion de Team Lock V2 en API, siguiente paso exacto del checkpoint.
2. Completar las operaciones criticas restantes de Fase 8 con permisos, consistencia y pruebas.
3. Fase 9: aislar parser y desarrollar la especificacion/implementacion autorizada del Companion.
4. Fase 10: frontend React y alojamiento previsto en Cloudflare.
5. Fase 11: migracion verificable de datos desde V1 y settings a V2.
6. Fase 12: comparacion/shadow mode.
7. Fase 13: staging con datos clonados.
8. Fase 14: medir rendimiento y corregir con datos.
9. Fase 15: cambio controlado del sistema principal.

### Por que se quiere migrar

Antonio se quejo de la sensacion de recarga al interactuar con Streamlit. React permite actualizar estados y componentes sin volver a ejecutar toda la pagina como hace el modelo actual. La separacion de API, dominio y persistencia tambien permite validar operaciones sin depender del cliente visual.

Cloudflare forma parte del plan de alojamiento del frontend. El beneficio de interaccion viene del cambio de arquitectura y de implementarlo bien; mover exactamente el mismo Streamlit a otro host no elimina por si solo sus reruns. El alojamiento final del backend debe respetar el FastAPI ya implementado y el parser, sin asumir que todo Python/C# puede ejecutarse igual en cualquier servicio.

No se han comprobado en esta tarea metricas del host ni se deben inventar caidas, limites de trafico o cifras de mejora. Los problemas concretos observados por Antonio fueron la experiencia de recarga, la inconsistencia visual y los fallos de presentacion que ha mostrado.

Fuentes: [project-checkpoint.md](project-checkpoint.md), [architecture.md](architecture.md), [migration-plan.md](migration-plan.md), [supabase-v2.md](supabase-v2.md), [security-rls.md](security-rls.md).

## 20. Companion / launcher: la experiencia futura que Antonio ha definido

Este apartado recoge decisiones del encargo de especificacion de Fase 9. No describe una herramienta terminada.

El requisito central es que el jugador no tenga que abrir PKHeX manualmente. Se puede seguir usando `PKHeX.Core` o el bridge C# internamente. Lo que debe desaparecer es el trabajo manual de exportar/importar Pokemon y volver a preparar saves para las acciones acordadas.

### Tres responsabilidades

La web/API es la autoridad de las decisiones oficiales: robo registrado, equipo fijado, estado de entrenador y operaciones permitidas. El Companion local conoce el archivo de partida, sincroniza su contenido, hace backups, ejecuta operaciones autorizadas y comunica el resultado. PKHeX.Core/bridge interpreta y serializa el formato real del juego.

El hecho oficial puede existir aunque el PC del jugador este apagado. La representacion en su save se aplica despues, con un estado visible pendiente/aplicado/fallido. Esto no autoriza a declarar aplicada una modificacion que aun no se ha validado en el archivo.

### Un solo archivo activo

El jugador selecciona una ruta y el Companion la recuerda localmente. Lee el contenido actual de ese mismo archivo cada vez que sincroniza o aplica una operacion. Detecta el juego/formato cuando sea posible. No tiene que detectar instalaciones o procesos de emuladores.

No se quiere una interfaz de conflictos con hashes y varios saves activos que el jugador tenga que resolver. Los hashes pueden existir internamente para deduplicar y diagnosticar. La ruta absoluta local tampoco necesita publicarse en el servidor.

### Operaciones concretas deseadas

La importacion del Pokemon robado debe tomar el ejemplar exacto y anadirlo al primer hueco libre de las cajas del receptor, en orden natural. No debe sobrescribir otro Pokemon ni reemplazar un miembro del equipo. Si no hay hueco, debe fallar de forma explicita.

Se acepta adaptar la propiedad del Pokemon al receptor si es la forma segura de que funcione correctamente y no desobedezca, preservando sus propiedades competitivas cuando sea posible. Esto requiere estudiar las relaciones entre OT, TID, SID, PID y formato; no consiste en cambiar campos al azar. La prioridad inicial son juegos/generaciones compatibles dentro de la competicion.

La retirada fisica del Pokemon de la victima no debe inventarse: hay que conservar la semantica aprobada del robo y distinguirla del import necesario para el receptor. El flujo web actual registra flags sin escribir el save.

El relleno de Caramelos Raros debe usar el maximo valido del juego detectado, no un 999 universal. La copia del equipo para Showdown debe leer el equipo actual y producir texto de importacion sin abrir PKHeX ni seleccionar manualmente seis archivos.

Fijar equipo sigue siendo una accion voluntaria que congela los seis Pokemon actuales mediante la API. No se dispara automaticamente al guardar partida. Tampoco se quiere un sistema general que edite el save despues de cada compra/canje.

### Seguridad del archivo y limites de producto

Antes de escribir se lee el archivo actual, se hace backup, se modifica en memoria, se serializa a un temporal, se vuelve a abrir y validar, se reemplaza de forma segura y se comprueba el resultado final. La retencion de backups debe ser configurable; no hay un numero arbitrario aprobado que deba inventarse.

No se quieren parches de ROM, inyeccion en RAM, deteccion de emuladores, correccion automatica de niveles, cementerio automatico ni un auditor universal de reglas. Una modificacion en disco puede requerir una recarga normal del juego para verse, y debe estudiarse como evitar que un guardado posterior desde memoria vieja la pise.

Los scripts locales de arranque y el wrapper Electron existentes no son este Companion. Abrir la URL de Streamlit en una ventana de escritorio no concede por si solo sincronizacion ni edicion segura de archivos.

## 21. Como trabajar con Antonio: preferencias observadas

Esta parte describe patrones expresados durante el proyecto. No pretende diagnosticar su personalidad ni inferir datos privados. Es contexto para colaborar mejor y reducir errores de interpretacion.

### Piensa con ejemplos visuales concretos

Antonio suele mostrar una captura y senalar elementos especificos: tamano del sprite, caja, tipo, boton, fondo o distribucion. Las referencias tienen peso funcional y estetico. Ante una imagen de Champions hay que identificar que composicion quiere trasladar, no limitarse a cambiar la paleta.

La consecuencia practica es responder con detalles verificables: que elemento se corrige, donde se ve y como queda la interaccion. Cuando diga que algo sigue enorme, comprobar altura, ancho, limites de imagen y CSS aplicado en esa pantalla concreta.

### Valora la coherencia completa

Ha detectado superficies secundarias antiguas despues de un redisenio principal: cambio de PIN, notificaciones, desplegables y Team Preview. Para el, la identidad de la app incluye esos recorridos, no solo la primera captura bonita.

Antes de declarar un acabado visual, hay que revisar las variantes relacionadas: propio/ajeno, con/sin datos, abierto/cerrado, seleccionado/vacio y distintos tamanos de pantalla. Ese trabajo no significa inventar una nueva direccion estetica.

### Quiere densidad util y comodidad

Rechaza mucho espacio muerto, fichas grandes sin informacion, iconos que dominan la pantalla y textos que explican lo evidente. Tambien rechaza encoger tanto que no se vean los Pokemon. Su preferencia observable es aprovechar el espacio sin perder legibilidad y poder consultar varias cosas de un vistazo.

La reduccion de texto en la web y su peticion de explicaciones largas para el proyecto no se contradicen. Son dos contextos distintos: interfaz de uso repetido breve; documentacion de traspaso exhaustiva.

### Se frustra ante resultados declarados que no aparecen

Ha repetido que no veia cambios o que seguia el mismo problema. Esto hace especialmente importante no equiparar editar un archivo con haber resuelto lo que ve en pantalla. Hay que verificar antes de dar un cambio por aplicado y reconocer con precision lo que sigue pendiente.

Si hay un fallo, explicar la causa concreta y corregirla. Evitar atribuir automaticamente el problema a que no ha recargado bien, a su navegador o a una accion suya sin evidencia.

### Prefiere autonomia con alcance claro

Cuando pide arreglar algo, espera trabajo concreto y un cierre, no una cadena de propuestas de continuar. Tambien ha fijado fases y limites muy estrictos: no empezar la siguiente, no tocar V1, no desplegar, no anadir mecanicas o no escribir en staging cuando no corresponde.

Su preferencia combina iniciativa dentro del encargo y respeto al plan. No interpreta que dar acceso a una herramienta autorice a cualquier cambio de datos o despliegue.

### Necesita instrucciones operativas situadas

En los pasos de Supabase y PowerShell pidio aclaraciones muy concretas: donde escribir un comando, como crear el archivo local, en que carpeta y que copiar exactamente. Dar una lista de acciones sin indicar el sitio no resuelve su necesidad.

Una instruccion util identifica aplicacion, ruta o pantalla, accion exacta, contenido o comando y resultado esperado. Si algo se puede ejecutar con el acceso ya disponible y esta autorizado, conviene hacerlo; si falta acceso, decir exactamente que falta.

No se debe confundir esta necesidad de especificidad con incapacidad para decidir producto. Antonio ha hecho decisiones detalladas sobre privacidad, snapshots, permisos, fases, ergonomia y automatizacion.

### Busca continuidad entre chats y herramientas

Utiliza otra IA para discutir y preparar encargos que despues ejecuta Codex. Perdio el contexto de una cuenta anterior y necesita documentos autosuficientes. No conviene escribir respuestas que solo se entienden recordando diez mensajes previos.

Tras una implementacion ha pedido dos niveles de cierre: uno breve para el, con lo realizado y estado de commit/push, y otro tecnico para la otra IA, con motivo, alcance, validacion, limitaciones y siguiente fase. No afirmar que hay commit, push, despliegue o pruebas reales si no se han hecho.

### Sus preferencias evolucionan y hay que respetar la ultima decision

Primero pidio fidelidad a Champions; despues una base menos clara; mas tarde una homogeneizacion conservadora y un freno al pulido continuo de Streamlit para avanzar en arquitectura. Una nueva IA no debe reiniciar la primera fase de estetica por leer una referencia antigua.

Con la sidebar paso de pedir que pudiera recuperarse a pedir que permaneciera siempre abierta. Con el Companion concreto que queria una ruta de save estable, sin deteccion de emuladores y sin automatizar todos los canjes. Esas precisiones posteriores prevalecen sobre propuestas anteriores mas amplias.

## 22. Diferencias y pendientes que una nueva IA no debe ocultar

| Tema | Realidad observada | Implicacion para continuar |
| --- | --- | --- |
| Estilo Champions | Referencia original clara/violeta; implementacion evolucionada a oscura. | Conservar composicion e identidad sin volver al exceso de luminosidad. |
| Cajas sin nombres | Peticion historica; renderer actual conserva metadatos. | No afirmar fidelidad exacta ni iniciar otro redisenio sin fase autorizada. |
| Seleccion del equipo | El renderer conserva Ver detalles. | No describir toda la UI como seleccion directa exclusiva del sprite. |
| Habilidad publica | Referencia visual la muestra; rama publica de Combate la omite. | Resolver el permiso del campo antes de copiar esa parte del diseno. |
| Compras | Tienda legacy tiene historial global; V2 restringe detalles. | Decidir proyeccion autorizada y equivalencia de producto antes de migrar la pantalla. |
| Juicios | Permisos por creador y visibilidad del caso. | No deducir admin-only por el grupo de sidebar. |
| Copa | Conserva configuracion/resultados/resets propios. | Auditar autorizacion al migrar; no dar por global la centralizacion de Liga. |
| Liga Finalizada del perfil | Bonus reclamable con ocho medallas y marca de una vez. | No confundir con finalizar temporada ni con verificar automaticamente el campeon del juego. |
| Economia en Normativa | Formula resumida omite partes del calculo real. | Consultar la implementacion y no usar ese resumen como contrato exhaustivo. |
| RLS V2 | Validada en V2; runtime sigue legacy. | No atribuir la proteccion nueva a todas las rutas actuales. |
| Animaciones | Los renderers piden sprites animados. | Comprobar carga y fallback; no prometer cobertura perfecta. |
| Documentos antiguos | Handover/backlog tienen referencias ya superadas. | Priorizar el checkpoint actual y contrastar el codigo. |

Estas observaciones son material para la siguiente fase y para explicaciones fieles. No autorizan a cambiar reglas, visibilidad, esquema o UI durante una tarea de documentacion.

## 23. Instrucciones de continuidad para la IA receptora

Antes de proponer trabajo, identifica que usa hoy el grupo y que existe solo como infraestructura futura. Comprueba rama, HEAD, estado local y `docs/project-checkpoint.md`. No publiques claves, tokens, PIN ni archivos `.env` en el contexto de otro chat.

Al hablar de una pestana, explica su recorrido real: que ve el usuario, que puede pulsar, que dato cambia, quien puede hacerlo y donde se ve el efecto. Si el codigo y la intencion difieren, nombra esa diferencia. No prometas funcionalidades por inferencia de un nombre de modulo o por lo que suele tener otra app Pokemon.

Para una tarea visual, conserva lo aprobado, revisa el resultado en navegador y las variantes relevantes. Para una migracion, conserva permisos, premios, privacidad, datos historicos y semantica de cada accion. Para una tarea de explicacion, no la conviertas en un despliegue o un cambio de mecanicas.

El siguiente paso tecnico registrado sigue siendo Fase 8C, Team Lock V2 API mutation. El objetivo global es llegar a una PokeApp mas fluida y mantenible, con la misma competicion que usa el grupo, una interfaz coherente y menos trabajo manual con saves, sin perder lo que ya funciona ni dar por terminado lo que aun esta planificado.
