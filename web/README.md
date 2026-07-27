# Optimizador de crianzas Diosesmon

SPA estatica para planificar crianzas de Pokemon en Cobblemon/Diosesmon. Todo corre en el navegador: no hay backend, base de datos, cuentas, cookies, `localStorage`, IndexedDB, analitica ni llamadas externas durante el uso normal.

## Que hace

- Gestiona reproductores en memoria durante la sesion.
- Valida grupos huevo, Ditto, sexos, proteccion, esterilidad y enfriamiento.
- Calcula descendencia esperada por regla de madre o progenitor no Ditto.
- Compara objetos de crianza, sexo forzado, presupuesto, inventario y coste de reposicion.
- Estima probabilidades de objetivo directo y de obtener un reproductor intermedio util.
- Ejecuta el optimizador en Web Worker con progreso y cancelacion.
- Permite registrar el huevo real, descontar dinero/objetos, deshacer y recalcular.
- Exporta/importa manualmente JSON validado.

## Que no hace todavia

- No afirma optimalidad global multigeneracional demostrada.
- No incluye dataset completo de todas las especies.
- No inventa reglas no confirmadas de Diosesmon.
- No calcula capturas, compras externas ni spawns si el usuario no los introduce.

## Instalacion

```bash
cd web
npm install
```

## Desarrollo

```bash
npm run dev
```

La app se abre en la URL local que indique Vite.

## Pruebas y build

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

`test:e2e` construye produccion y ejecuta Playwright contra `vite preview`.

## Despliegue estatico

Vercel:

```bash
cd web
npm install
npm run build
```

Configura:

- Framework: Vite
- Build command: `npm run build`
- Output directory: `dist`

Cloudflare Pages:

- Build command: `npm run build`
- Build output directory: `dist`
- Root directory: `web`

GitHub Pages:

```bash
cd web
npm run build
```

Publica el contenido de `web/dist`.

## Arquitectura

- `src/domain`: tipos puros de Pokemon, economia, tiempo y optimizacion.
- `src/engine`: compatibilidad, descendencia, herencia, costes, scheduling y optimizador.
- `src/rules`: perfiles de servidor. El perfil inicial es `Diosesmon - reglas en verificacion`.
- `src/data`: JSON local versionado.
- `src/state`: estado de sesion en memoria con undo/redo.
- `src/workers`: Web Worker del optimizador.
- `src/pages` y `src/components`: interfaz React en espanol.
- `src/tests`: unitarias, propiedades e integracion.
- `tests/e2e`: Playwright.

## Reglas Diosesmon

Confirmado por defecto:

- Crianza: 2.500 $
- Duracion: 25 minutos
- Forzar sexo: 5.000 $
- Objeto: 500 $
- Objetos consumibles y maximo un objeto por progenitor
- Sin Ditto, la cria sigue la linea de la madre
- Con Ditto, la cria sigue el progenitor no Ditto

Pendiente/configurable:

- Formula exacta de herencia
- IV no heredados
- Interaccion Lazo Destino + objetos recios
- Dos objetos recios y conflictos de estadistica
- Probabilidades de habilidad/naturaleza
- Enfriamiento, ranuras, esterilidad y excepciones

## Algoritmo

El primer motor evalua parejas compatibles, roles de madre/padre, especie resultante, planes de objetos, sexo forzado opcional, coste directo, coste de reposicion, tiempo, probabilidad directa y utilidad como reproductor intermedio. Despues separa acciones dominadas y ordena las alternativas por modo barato, rapido o equilibrado.

La UI muestra:

- `Mejor estrategia encontrada` en busqueda rapida.
- `Optima dentro de los limites de busqueda` en busqueda precisa.

No se muestra `Optimo demostrado` para el plan completo porque la busqueda multigeneracional exhaustiva completa todavia no esta implementada.

## Datos de especies

Los datos iniciales viven en:

- `src/data/species.generated.json`
- `src/data/egg-groups.generated.json`
- `src/data/abilities.generated.json`
- `src/data/data-version.json`

El dataset es minimo para el nucleo funcional y los fixtures. Antes de un uso amplio conviene sustituirlo por un dataset completo verificable y mantener la procedencia en `data-version.json`.

## Privacidad

La aplicacion no guarda nada automaticamente. Al recargar se pierde el criadero. La exportacion JSON solo ocurre cuando el usuario pulsa el boton correspondiente.

## Documentacion tecnica

- [Motor de reglas](docs/rules-engine.md)
- [Optimizador](docs/optimizer.md)
- [Modelo probabilistico](docs/probability-model.md)
- [Perfiles de servidor](docs/server-profiles.md)
- [Fuentes de datos](docs/data-sources.md)
- [Privacidad](docs/privacy.md)
