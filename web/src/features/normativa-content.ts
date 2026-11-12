// The ChampionsLocke rulebook: static, versioned content. Precedence when the
// sources disagree: owner decisions, then the rules live in the League, then
// the original PDF. Nothing here reads or changes competitive data.
import { points } from "../points";

export const rulebookUpdated = "12 de noviembre de 2026";

export type RuleKind =
  "norma" | "obligatorio" | "prohibido" | "excepcion" | "aclaracion";
export type Rule = { id: string; kind: RuleKind; text: string };

export const chapters = [
  { id: "nuzlocke", numeral: "I", title: "Normas Nuzlocke" },
  { id: "niveles", numeral: "II", title: "Límites de nivel" },
  { id: "jornadas", numeral: "III", title: "Tramos y jornadas" },
  { id: "competicion", numeral: "IV", title: "Sistema competitivo" },
  { id: "partida", numeral: "V", title: "Partida y conducta" },
  { id: "comodines", numeral: "VI", title: "Interacciones y comodines" },
  { id: "otras", numeral: "VII", title: "Otras reglas vigentes" },
] as const;

export const ruleLegend: { kind: RuleKind; label: string; hint: string }[] = [
  { kind: "norma", label: "Norma", hint: "Cómo se juega" },
  { kind: "obligatorio", label: "Obligatorio", hint: "Tienes que hacerlo" },
  { kind: "prohibido", label: "Prohibido", hint: "No se puede hacer" },
  { kind: "excepcion", label: "Excepción", hint: "Cuándo no se aplica" },
  { kind: "aclaracion", label: "Aclaración", hint: "Para entenderlo mejor" },
];

// ---------- I. Normas Nuzlocke ----------
export type NuzlockeGroup = {
  id: "capturas" | "caja" | "clausulas" | "shiny" | "tiendas";
  title: string;
  rules: Rule[];
};
export const nuzlockeGroups: NuzlockeGroup[] = [
  {
    id: "capturas",
    title: "Capturas y rutas",
    rules: [
      {
        id: "1.1",
        kind: "norma",
        text: "Solo puedes capturar el primer Pokémon salvaje de cada ruta o zona.",
      },
      {
        id: "1.2",
        kind: "obligatorio",
        text: "Todos tus Pokémon deben llevar mote.",
      },
      {
        id: "1.3",
        kind: "norma",
        text: "Si el primer Pokémon de la ruta es derrotado, huye, abandonas el combate o el combate termina de cualquier otra forma, pierdes la captura de esa ruta.",
      },
    ],
  },
  {
    id: "caja",
    title: "Caja de muertos",
    rules: [
      {
        id: "1.4",
        kind: "obligatorio",
        text: "Todo Pokémon debilitado debe guardarse en la caja de muertos. En ChampionsLocke es la Caja 7.",
      },
      {
        id: "1.5",
        kind: "prohibido",
        text: "Usar un Pokémon debilitado para cualquier función o subirlo de nivel.",
      },
      {
        id: "1.6",
        kind: "excepcion",
        text: "Sí puede seguir sirviendo como esclavo de MO.",
      },
    ],
  },
  {
    id: "clausulas",
    title: "Duplicados y legendarios",
    rules: [
      {
        id: "1.7",
        kind: "norma",
        text: "Cláusula de duplicados. Si el primer Pokémon de una zona ya está en tu poder, o tienes a cualquiera de su línea evolutiva, fuerza encuentros hasta que aparezca uno que no hayas capturado.",
      },
      {
        id: "1.8",
        kind: "prohibido",
        text: "Cláusula de legendarios. No se permiten Pokémon legendarios.",
      },
      {
        id: "1.9",
        kind: "norma",
        text: "Si el primer Pokémon de una zona es legendario, fuerza encuentros hasta que aparezca uno que no lo sea.",
      },
    ],
  },
  {
    id: "shiny",
    title: "Cláusula shiny",
    rules: [
      {
        id: "1.10",
        kind: "excepcion",
        text: "Puedes capturar cualquier Pokémon shiny que encuentres, sea o no el primer encuentro de su zona.",
      },
      {
        id: "1.11",
        kind: "excepcion",
        text: "Si el primer Pokémon de una ruta es shiny, puedes capturarlo y no cuenta como el primero de esa ruta.",
      },
      {
        id: "1.12",
        kind: "prohibido",
        text: "Forzar la aparición de shinies.",
      },
      {
        id: "1.13",
        kind: "norma",
        text: "Si encuentras un shiny de una especie que ya tienes, contando todas sus fases evolutivas y evoluciones alternativas, puedes elegir con cuál quedarte y liberar el otro.",
      },
      {
        id: "1.14",
        kind: "excepcion",
        text: "Eevee queda fuera de esta regla: sus evoluciones alternativas no cuentan.",
      },
    ],
  },
  {
    id: "tiendas",
    title: "Tiendas del juego",
    rules: [
      {
        id: "1.15",
        kind: "prohibido",
        text: "Comprar objetos de combate u objetos curativos en las tiendas.",
      },
      {
        id: "1.16",
        kind: "norma",
        text: "Cada objeto solo puede comprarse una vez.",
      },
      {
        id: "1.17",
        kind: "aclaracion",
        text: "Estas normas hablan de las tiendas de tu partida. La Tienda de PokeApp funciona por su cuenta y se explica en el capítulo VI.",
      },
    ],
  },
];
export const rulesCanChange: Rule = {
  id: "1.18",
  kind: "norma",
  text: "Las normas pueden editarse en cualquier momento para añadir cosas que mejoren la experiencia de juego y el equilibrio de la competición.",
};
export const aaronClause: Rule = {
  id: "1.19",
  kind: "norma",
  text: "Aarón no podrá buscar vacíos legales ni lagunas en las normas.",
};

// ---------- II. Límites de nivel ----------
export type Challenge = {
  name: string;
  label: string;
  level: number;
  type: string;
  badge?: number;
  elite?: boolean;
};
export type Stretch = {
  number: 1 | 2 | 3 | 4;
  matchday: 1 | 2 | 3 | 4;
  cap: number;
  capLeader: string;
  ends: string;
  challenges: Challenge[];
};
export const stretches: Stretch[] = [
  {
    number: 1,
    matchday: 1,
    cap: 30,
    capLeader: "Lino",
    ends: "Termina al derrotar al segundo líder, Lino.",
    challenges: [
      {
        name: "Violeta",
        label: "Gimnasio 1",
        level: 14,
        type: "bug",
        badge: 1,
      },
      { name: "Lino", label: "Gimnasio 2", level: 30, type: "rock", badge: 2 },
    ],
  },
  {
    number: 2,
    matchday: 2,
    cap: 41,
    capLeader: "Amaro",
    ends: "Termina al derrotar al cuarto líder, Amaro.",
    challenges: [
      {
        name: "Corelia",
        label: "Gimnasio 3",
        level: 38,
        type: "fighting",
        badge: 3,
      },
      {
        name: "Amaro",
        label: "Gimnasio 4",
        level: 41,
        type: "grass",
        badge: 4,
      },
    ],
  },
  {
    number: 3,
    matchday: 3,
    cap: 50,
    capLeader: "Valeria",
    ends: "Termina al derrotar a la sexta líder, Valeria.",
    challenges: [
      {
        name: "Lem",
        label: "Gimnasio 5",
        level: 44,
        type: "electric",
        badge: 5,
      },
      {
        name: "Valeria",
        label: "Gimnasio 6",
        level: 50,
        type: "fairy",
        badge: 6,
      },
    ],
  },
  {
    number: 4,
    matchday: 4,
    cap: 82,
    capLeader: "Dianta",
    ends: "Termina al acabar el juego.",
    challenges: [
      {
        name: "Astrid",
        label: "Gimnasio 7",
        level: 58,
        type: "psychic",
        badge: 7,
      },
      { name: "Edel", label: "Gimnasio 8", level: 70, type: "ice", badge: 8 },
      {
        name: "Alto Mando",
        label: "Cuatro combates",
        level: 78,
        type: "dragon",
        elite: true,
      },
      { name: "Dianta", label: "Campeona", level: 82, type: "fairy" },
    ],
  },
];
export const eliteTypes = ["steel", "dragon", "fire", "water"] as const;
export const eliteNote =
  "El Alto Mando lo forman Tileo, Trazena, Malva y Narciso, todos con límite de nivel 78.";

export const levelRules: Rule[] = [
  {
    id: "2.1",
    kind: "norma",
    text: "Ningún Pokémon de tu partida puede superar el nivel del Pokémon más fuerte del siguiente líder al que vayas a enfrentarte.",
  },
  {
    id: "2.2",
    kind: "obligatorio",
    text: "El Pokémon que supere el límite no podrá utilizarse y deberá guardarse en la caja.",
  },
  {
    id: "2.3",
    kind: "norma",
    text: "Los Caramelos Raros solo pueden usarse delante del líder de gimnasio correspondiente.",
  },
  {
    id: "2.4",
    kind: "excepcion",
    text: "También puedes usarlos para ajustar un Pokémon al nivel de tu equipo.",
  },
  {
    id: "2.5",
    kind: "excepcion",
    text: "Si al usar Caramelos Raros subes un Pokémon por accidente por encima del límite, puedes hacer reset para ajustar el nivel, siempre que hubieras guardado la partida antes.",
  },
];

// ---------- III. Tramos y jornadas ----------
export const stretchRules: Rule[] = [
  {
    id: "3.1",
    kind: "norma",
    text: "La partida se divide en cuatro tramos. Al terminar cada tramo se celebra una jornada de Liga.",
  },
  {
    id: "3.2",
    kind: "norma",
    text: "El nivel de los Pokémon en los combates lo marca el último líder del tramo.",
  },
];
export const matchdaySteps = [
  {
    title: "Sincroniza tu partida",
    text: "Registra tu partida oficial con PokeApp Launcher. Para abrir la primera jornada, todos deben tener las dos primeras medallas.",
  },
  {
    title: "Fija tu equipo",
    text: "Pulsa «Fijar Equipo» antes de que se abra la jornada. Tu equipo queda registrado y se anuncia en Discord.",
  },
  {
    title: "Se abre la jornada",
    text: "Cualquier participante activo la abre desde Liga, en General. Si falta algo, el botón indica qué falta y de quién.",
  },
  {
    title: "Combates todos contra todos",
    text: "Cada entrenador se enfrenta una vez a cada rival con el equipo que fijó.",
  },
  {
    title: "Se registran los resultados",
    text: "En la pestaña de la jornada, cualquier participante marca al ganador de cada combate. Se puede revisar hasta el cierre.",
  },
  {
    title: "Se cierra la jornada",
    text: "Con todos los combates registrados, cualquier participante la cierra. Se congela su clasificación y se reparten monedas y premios.",
  },
];
export const teamPanels = [
  {
    id: "fijar",
    title: "Fijar Equipo",
    points: [
      "Está en tu ficha de entrenador y en Batallas, dentro de Team Preview.",
      "Fija los seis Pokémon del equipo de tu partida oficial. Si tienes menos de seis, no podrás hacerlo.",
      "Hazlo antes de que se abra la jornada. Si tu primer equipo llega con la jornada abierta, queda registrado como fuera de plazo.",
      "Puedes fijarlo de nuevo hasta que se cierre la jornada. Vale el último confirmado y cada confirmación se anuncia en Discord.",
    ],
  },
  {
    id: "lock",
    title: "Team Lock",
    points: [
      "Es el registro oficial de tus seis Pokémon para esa jornada.",
      "El equipo que tengas en la partida no lo sustituye: si falta, PokeApp te avisa de que está pendiente.",
      "El anuncio en Discord enlaza a Pokepast.es con especie, forma, mote, género, nivel, objeto, movimientos y shiny. Nunca muestra habilidad, naturaleza, IVs ni EVs.",
    ],
  },
  {
    id: "preview",
    title: "Team Preview",
    points: [
      "Lo tienes en Batallas y está disponible siempre, haya jornada o no.",
      "Si un entrenador ya tiene Team Lock, ves su equipo oficial. Si no, ves su equipo actual marcado como provisional.",
      "En modo Espectador comparas dos equipos públicos. En modo Batalla consultas uno; tus datos privados solo aparecen al elegirte a ti.",
    ],
  },
];
export const matchdayStates = [
  {
    id: "preparada",
    title: "Preparada",
    text: "La jornada existe, pero aún no se combate. Es el momento de fijar el equipo.",
  },
  {
    id: "abierta",
    title: "Abierta",
    text: "Se juegan los combates y se registran o revisan sus resultados.",
  },
  {
    id: "cerrada",
    title: "Cerrada",
    text: "Su clasificación queda congelada. Solo Administración puede corregirla, con un procedimiento auditado.",
  },
];

// ---------- IV. Sistema competitivo ----------
export const scoreTiles = [
  { id: "win", value: "+1", label: "Victoria" },
  { id: "loss", value: "0", label: "Derrota" },
  { id: "death", value: "−0,1", label: "Muerte ordinaria" },
  { id: "wipe", value: "−0,2", label: "Muerte revivida tras wipe, en total" },
];
export const scoreRules: Rule[] = [
  {
    id: "4.1",
    kind: "norma",
    text: "Una misma muerte nunca se penaliza dos veces.",
  },
  {
    id: "4.2",
    kind: "norma",
    text: "Revivir un Pokémon no elimina la muerte registrada.",
  },
  {
    id: "4.3",
    kind: "norma",
    text: "Los puntos NET acumulados determinan la clasificación general y el campeón.",
  },
  {
    id: "4.4",
    kind: "aclaracion",
    text: "Los puntos NET se calculan igual con la jornada preparada, abierta o cerrada: cuentan las victorias y las muertes registradas hasta ese momento.",
  },
  {
    id: "4.5",
    kind: "aclaracion",
    text: "Un wipe ocurre cuando se debilita todo tu equipo y el juego te devuelve a un Centro Pokémon con todos curados. Esos Pokémon no llegan a la caja: anótalos en tu ficha, en «Revividos tras wipe».",
  },
  {
    id: "4.6",
    kind: "aclaracion",
    text: "Las demás muertes se leen automáticamente de tu partida oficial al sincronizarla.",
  },
  {
    id: "4.7",
    kind: "aclaracion",
    text: "Una sanción de puntos decidida en un juicio se resta aparte de esta fórmula.",
  },
];
export type Example = {
  wins: number;
  ordinary: number;
  wipe: number;
  note: string;
};
export const examples: Example[] = [
  {
    wins: 3,
    ordinary: 2,
    wipe: 0,
    note: "3 victorias y 2 muertes ordinarias",
  },
  {
    wins: 1,
    ordinary: 1,
    wipe: 1,
    note: "1 victoria, 1 muerte ordinaria y 1 muerte revivida tras wipe",
  },
  {
    wins: 0,
    ordinary: 3,
    wipe: 0,
    note: "Ninguna victoria y 3 muertes ordinarias",
  },
];

/** NET in exact tenths: never computed through binary floating point. */
export function netTenths(wins: number, ordinary: number, wipe: number) {
  return wins * 10 - ordinary - wipe * 2;
}
export function netText(wins: number, ordinary: number, wipe: number) {
  const tenths = netTenths(wins, ordinary, wipe),
    size = Math.abs(tenths);
  const text = points(
    `${tenths < 0 ? "-" : ""}${Math.floor(size / 10)}.${size % 10}`,
  );
  return text.replace("-", "−");
}

export const formatFacts = [
  {
    title: "Una sola Liga",
    text: "Todos compiten en la misma clasificación. No hay divisiones, ascensos ni descensos.",
  },
  {
    title: "Todos contra todos",
    text: "En cada jornada combates una vez contra cada rival. Con seis entrenadores son 15 combates por jornada, cinco para cada uno.",
  },
  {
    title: "Cuatro jornadas",
    text: "Una por tramo. La cuarta se juega al terminar el juego.",
  },
];
export const standings = [
  {
    title: "Clasificación de jornada",
    text: "Se ordena por victorias. A igualdad de victorias va delante quien haya tenido menos muertes durante ese tramo.",
    detail:
      "Si un empate afecta al podio, al primer puesto o al último, se resuelve con combates 1v1 adicionales entre los empatados. No suman puntos ni victorias, y se registran al cerrar la jornada con fecha y evidencia. Si no afecta a nada de eso, los empatados comparten posición.",
  },
  {
    title: "Clasificación general",
    text: "Se ordena por los puntos NET acumulados.",
    detail:
      "Gana la Liga quien tenga más puntos NET al terminar la cuarta jornada.",
  },
];
export const titleTiebreak = [
  {
    title: "Menos muertes totales del Locke",
    text: "Cada muerte cuenta una sola vez, incluidas las de Pokémon revividos con comodines o tras un wipe.",
  },
  {
    title: "Combate de desempate 1v1",
    text: "Si las muertes también empatan o falta el historial oficial, deciden los combates 1v1 registrados.",
  },
];
export const titleTiebreakNote =
  "Administración registra el método y la evidencia. Este desempate solo decide el título: no cambia puntos, victorias, muertes ni premios de las jornadas.";
export const prizes = [
  {
    id: "todos",
    who: "Todos los participantes",
    what: "10 monedas por cada jornada cerrada",
  },
  {
    id: "primero",
    who: "Primero de la jornada",
    what: "Blindar Pokémon extra",
    code: "blindar_pokemon",
  },
  {
    id: "ultimo",
    who: "Último de la jornada",
    what: "Robar Pokémon extra",
    code: "robar_pokemon",
  },
  {
    id: "campeon",
    who: "Campeón de Liga",
    what: "Su nombre en el Hall de la Fama",
  },
];

// ---------- V. Partida y conducta ----------
export const discordRules: Rule[] = [
  {
    id: "5.1",
    kind: "obligatorio",
    text: "Juega siempre en directo en el canal de Discord.",
  },
  {
    id: "5.2",
    kind: "obligatorio",
    text: "Avisa antes por el grupo de WhatsApp.",
  },
];
export const freeItemRules: Rule[] = [
  {
    id: "5.3",
    kind: "norma",
    text: "Dispones de Caramelos Raros y Escamas Corazón ilimitados.",
  },
  {
    id: "5.4",
    kind: "aclaracion",
    text: "Se añaden gratis a la bolsa desde tu inventario, con PokeApp Launcher.",
  },
  {
    id: "5.5",
    kind: "prohibido",
    text: "Vender estos objetos para conseguir dinero o cualquier otro beneficio dentro del juego.",
  },
];
export const conductRules: Rule[] = [
  {
    id: "5.6",
    kind: "prohibido",
    text: "En las tiendas del juego, comprar objetos de combate u objetos curativos, o repetir la compra de un objeto.",
  },
  {
    id: "5.7",
    kind: "obligatorio",
    text: "Respeta este reglamento y las reglas de la competición en todo momento.",
  },
];

// ---------- VI. Interacciones y comodines ----------
export const tradeRules: Rule[] = [
  {
    id: "6.1",
    kind: "norma",
    text: "Puedes intercambiar Pokémon con otros jugadores.",
  },
  {
    id: "6.2",
    kind: "norma",
    text: "Cada jugador tiene un intercambio por cada tramo.",
  },
  {
    id: "6.3",
    kind: "prohibido",
    text: "Intercambiar pseudo-legendarios.",
  },
  {
    id: "6.4",
    kind: "prohibido",
    text: "Incluir objetos en un intercambio.",
  },
];
export const practiceRule: Rule = {
  id: "6.5",
  kind: "norma",
  text: "Se permiten combates de práctica fuera de la ronda de combates.",
};
export const wildcardRule: Rule = {
  id: "6.6",
  kind: "norma",
  text: "Puedes usar tus cartas comodín contra otros jugadores o sobre ti mismo, según lo que permita cada carta.",
};

export type Wildcard = {
  code: string;
  name: string;
  price: number | null;
  effect: string;
  note: string;
  active: boolean;
  status: string;
};
export const wildcards: Wildcard[] = [
  {
    code: "blindar_pokemon",
    name: "Blindar Pokémon",
    price: 12,
    effect:
      "Protege a uno de tus Pokémon vivos: queda BLINDADO y no se puede robar.",
    note: "Un Pokémon muerto o ya blindado no puede blindarse.",
    active: true,
    status: "Disponible",
  },
  {
    code: "revivir_pokemon",
    name: "Revivir Pokémon",
    price: 12,
    effect:
      "Devuelve a la vida a un Pokémon de tu Caja 7. Queda REVIVIDO y BLINDADO.",
    note: "Su muerte sigue registrada y la penalización NET no desaparece.",
    active: true,
    status: "Disponible. Se usa cuando quieras desde PokeApp Launcher.",
  },
  {
    code: "robar_pokemon",
    name: "Robar Pokémon",
    price: 12,
    effect:
      "Te llevas un Pokémon de otro participante. Queda ROBADO y BLINDADO, y conserva su historia.",
    note: "Quien roba recibe un vale de Blindaje por Robo.",
    active: true,
    status: "Disponible. Se guarda y se usa cuando quieras.",
  },
  {
    code: "captura_extra",
    name: "Captura Extra",
    price: 5,
    effect: "Permiso para hacer una captura adicional.",
    note: "Se usa desde tu inventario y no va a la bolsa.",
    active: true,
    status: "Disponible",
  },
  {
    code: "fosil",
    name: "Fósil",
    price: 5,
    effect: "Eliges qué fósil quieres.",
    note: "PokeApp Launcher lo añade a tu bolsa.",
    active: true,
    status: "Disponible",
  },
  {
    code: "robbery_shield_voucher",
    name: "Blindaje por Robo",
    price: null,
    effect: "Vale para blindar a uno de tus Pokémon.",
    note: "No se compra: lo recibe quien completa un robo.",
    active: true,
    status: "Se recibe al completar un robo.",
  },
];
export const robberyRules: Rule[] = [
  {
    id: "6.7",
    kind: "prohibido",
    text: "Usar Robo de Pokémon sobre un jugador que ya haya sido robado en la ronda actual. Nadie puede volver a ser víctima hasta que todos los demás entrenadores que se pueden robar lo hayan sido también.",
  },
  {
    id: "6.8",
    kind: "prohibido",
    text: "Usar Robo de Pokémon antes de que pasen 24 horas desde la captura del Pokémon objetivo.",
  },
  {
    id: "6.9",
    kind: "norma",
    text: "Solo se puede robar entre partidas del mismo juego: de X a X y de Y a Y.",
  },
  {
    id: "6.10",
    kind: "norma",
    text: "No se puede robar un Pokémon muerto, blindado, ya robado o recibido de otro entrenador, ni el último Pokémon del equipo de un rival.",
  },
  {
    id: "6.11",
    kind: "aclaracion",
    text: "La víctima no puede rechazar un robo válido: PokeApp es quien lo decide.",
  },
  {
    id: "6.12",
    kind: "norma",
    text: "Robar se puede usar en cualquier momento: no hace falta Team Lock ni que haya una jornada abierta, y no depende de los combates. El comodín se compra y se guarda para cuando quieras.",
  },
  {
    id: "6.13",
    kind: "norma",
    text: "La rotación de víctimas es global y compartida por toda la Liga: cuando todos los entrenadores que se pueden robar han sido víctimas, empieza una nueva ronda.",
  },
  {
    id: "6.14",
    kind: "aclaracion",
    text: "Las 24 horas se cuentan desde la primera vez que PokeApp ve a ese Pokémon en una partida sincronizada. Los Pokémon blindados están protegidos.",
  },
  {
    id: "6.15",
    kind: "norma",
    text: "Revivir se compra y se guarda; se usa cuando quieras desde PokeApp Launcher, sin Team Lock y sin depender de las jornadas. Recupera un Pokémon muerto de la Caja 7.",
  },
  {
    id: "6.16",
    kind: "aclaracion",
    text: "Revivir no borra la muerte: sigue en tu historial y la penalización NET no desaparece. Revivir no cobra ninguna penalización nueva.",
  },
];
export const shopFacts = [
  {
    title: "Cómo se ganan monedas",
    text: "4 por cada medalla, 12 por vencer a la Campeona y 10 por cada jornada cerrada. Las de medallas y Campeona se abonan solas al sincronizar tu partida oficial.",
  },
  {
    title: "Qué se vende",
    text: "Comodines, bayas, objetos competitivos y objetos de crianza. El precio se paga al confirmar la compra.",
  },
  {
    title: "Cómo llega a tu partida",
    text: "Los objetos del juego se añaden a tu bolsa una sola vez con PokeApp Launcher. Si un objeto no existe en tu juego, la Tienda te lo indica.",
  },
  {
    title: "Ofertas",
    text: "Al cerrar una jornada pueden anunciarse ofertas para la siguiente. Se activan 24 horas después, tienen unidades limitadas y cada entrenador puede aprovechar cada oferta una sola vez. Terminan al cerrarse esa jornada.",
  },
];

// ---------- VII. Otras reglas vigentes ----------
export const otherRules = [
  {
    id: "7.1",
    title: "Partida oficial",
    text: "Cada entrenador compite con su partida oficial de la Liga, registrada y sincronizada con PokeApp Launcher. La primera jornada no se abre hasta que todos la tengan.",
  },
  {
    id: "7.2",
    title: "Recompensas de progreso",
    text: "Las monedas de medallas y Campeona se entregan una sola vez por cada hito.",
  },
  {
    id: "7.3",
    title: "Felicidad máxima",
    text: "Gratis e ilimitada. Sube a 255 la felicidad de un Pokémon de tu equipo o de tus cajas del PC (sin moverlo) desde tu inventario en PokeApp Launcher. No cambia nada más ni lo hace evolucionar por sí sola.",
  },
  {
    id: "7.4",
    title: "Entrenadores nuevos",
    text: "Administración puede incorporar a un entrenador con la Liga en marcha. Empieza con 0 puntos, no juega las jornadas ya cerradas y recibe las monedas que esas jornadas repartieron. Las medallas que ya tuviera no dan monedas.",
  },
  {
    id: "7.5",
    title: "Juicios y sanciones",
    text: "Cualquier participante puede abrir un juicio en la sección Juicios. La decisión se toma en Discord y queda registrada en PokeApp. Puede terminar en bloqueo de tienda, reducción de monedas o de puntos, liberación de un Pokémon u otra medida.",
  },
  {
    id: "7.6",
    title: "Copa",
    text: "El documento original reservó un apartado para la Copa, pero no llegó a definir sus normas. Se publicarán aquí cuando se aprueben.",
  },
];
