const fs = require("node:fs");
const path = require("node:path");
if (!process.env.POKEAPP_PACKAGE_STAGE || !process.env.POKEAPP_PACKAGE_OUTPUT)
  throw new Error("Use tools/build_launcher_windows.ps1");
const privateCandidate = process.env.POKEAPP_PRIVATE_CANDIDATE === "1";
// Updates: only the PUBLIC key and an HTTPS feed are baked in, together or not
// at all. Without both, the shipped updater stays disabled.
const updateKeyFile = process.env.POKEAPP_UPDATE_PUBLIC_KEY_FILE || "";
const updateFeed = process.env.POKEAPP_UPDATE_FEED || "";
if (!!updateKeyFile !== !!updateFeed)
  throw new Error("Update public key and feed must be configured together");
if (updateFeed && !updateFeed.startsWith("https://"))
  throw new Error("Update feed must use HTTPS");
const updateKey = updateKeyFile ? fs.readFileSync(updateKeyFile, "utf8") : null;
if (updateKey && /PRIVATE KEY/.test(updateKey))
  throw new Error("Refusing to embed a private key");
// Disposable version numbers are for private candidates only.
const buildVersion = process.env.POKEAPP_BUILD_VERSION || "";
if (buildVersion && !privateCandidate)
  throw new Error("Version override is limited to private candidates");
const channel = privateCandidate ? "private" : "stable";
const productName = privateCandidate
  ? "PokeApp Launcher Private"
  : "PokeApp Launcher";

module.exports = {
  appId: privateCandidate
    ? "app.pokeapp.launcher.private"
    : "app.pokeapp.launcher",
  productName,
  artifactName: privateCandidate
    ? "PokeApp-Launcher-Private-Setup.exe"
    : "PokeApp-Launcher-Setup.exe",
  extraMetadata: {
    pokeappPrivateCandidate: privateCandidate,
    ...(buildVersion ? { version: buildVersion } : {}),
    ...(updateKey
      ? {
          pokeappUpdate: {
            publicKey: updateKey,
            feed: { stable: null, private: null, [channel]: updateFeed },
          },
        }
      : {}),
  },
  asar: true,
  npmRebuild: false,
  directories: { output: process.env.POKEAPP_PACKAGE_OUTPUT },
  files: [
    "main.cjs",
    "preload.cjs",
    "renderer.js",
    "index.html",
    "style.css",
    "package.json",
    "assets/icon.ico",
    "assets/items/50.png",
    "assets/items/93.png",
    "quantity.js",
    "updater.cjs",
  ],
  extraResources: [
    {
      from: process.env.POKEAPP_PACKAGE_STAGE,
      to: "runtime",
      filter: ["**/*", "!**/*.pdb", "!**/*.pyc", "!**/__pycache__/**"],
    },
  ],
  win: {
    target: [{ target: "nsis", arch: ["x64"] }],
    icon: path.join(__dirname, "assets/icon.ico"),
    executableName: productName,
    requestedExecutionLevel: "asInvoker",
    signAndEditExecutable: true,
  },
  nsis: {
    oneClick: false,
    perMachine: false,
    allowElevation: false,
    allowToChangeInstallationDirectory: true,
    createDesktopShortcut: false,
    createStartMenuShortcut: true,
    shortcutName: productName,
    deleteAppDataOnUninstall: false,
    runAfterFinish: false,
  },
  publish: null,
};
