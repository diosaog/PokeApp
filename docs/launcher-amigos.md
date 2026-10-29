# PokeApp Launcher: instalar, entrar y vincular tu partida

Versión actual: **0.26.8** (Windows 10 y 11). No hace falta ser administrador.

## Si todavía no lo tienes

1. Descarga el instalador:
   https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download
2. Ábrelo. Si Windows dice «Windows protegió tu PC», pulsa
   **Más información → Ejecutar de todas formas** (el instalador es privado y
   no lleva firma de Microsoft; el Launcher comprueba él mismo sus
   actualizaciones).
3. Al terminar no se abre solo: busca **PokeApp Launcher** en el menú Inicio.
4. Entra con tu cuenta de PokeApp. La sesión se queda guardada.

## Si ya lo tenías

- Si te ofrece la **0.26.8**, pulsa **Actualizar**. Se cierra y vuelve a abrirse
  solo.
- Si no se actualiza, o se queda en «Sin conexión» o «El núcleo del Launcher
  está tardando en responder»:
  1. Cierra el Launcher.
  2. Descarga el instalador del enlace de arriba y ejecútalo encima. No
     desinstales nada.
  3. Vuelve a abrirlo desde el menú Inicio.

  Tu sesión, tu partida elegida y tus copias de seguridad se conservan: están
  guardadas en tu usuario de Windows, no en la carpeta del programa.

## Vincular tu partida

1. Cierra el emulador.
   Comprueba que has entrado en tu propia cuenta de PokeApp.
2. En el Launcher: **Saves y Launcher → Buscar partidas en un emulador**
   (Lime3DS, Azahar o Citra).
3. Elige tu partida. Si no aparece, usa **Elegir archivo…**.
4. A partir de ahí se sincroniza sola cada vez que guardas. No hace falta
   reiniciar nada.

## Añadir un objeto comprado

Con el emulador cerrado, abre **Inventario → Añadir a la bolsa** y confirma
el objeto en el Launcher. Se entrega en la partida vinculada a tu Liga y se
guarda una copia antes de escribir. Si queda pendiente de comprobar, vuelve a
abrir el Launcher y conserva las copias; la compra sigue reservada mientras
se recupera. Los Caramelos Raros y las Escamas Corazón siguen en **Objetos ∞**.

## Comprobación (30 segundos)

En **Saves y Launcher → Launcher** debe poner:

- Núcleo local: **Disponible**
- Conexión con PokeApp: **Conectado**
- Cuenta: tu nombre

Si alguna línea dice otra cosa durante más de un minuto, pulsa
**Copiar diagnóstico** y envía el texto. No contiene tu contraseña, tu PIN ni
tu partida.

La aceptación en cada PC sigue pendiente: comprueba tu nombre de cuenta,
cierra y abre para confirmar que conserva la sesión y la partida, guarda
desde el emulador y verifica que PokeApp muestra la sincronización.

Si aparece «Windows no deja ejecutar el núcleo del Launcher», el antivirus lo
ha bloqueado: restaura `PokeApp.Core.exe` desde la cuarentena del antivirus o
vuelve a instalar.
