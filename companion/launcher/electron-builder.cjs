const path = require("node:path");
if (!process.env.POKEAPP_PACKAGE_STAGE || !process.env.POKEAPP_PACKAGE_OUTPUT)
  throw new Error("Use tools/build_launcher_windows.ps1");
const privateCandidate = process.env.POKEAPP_PRIVATE_CANDIDATE === "1";
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
  extraMetadata: { pokeappPrivateCandidate: privateCandidate },
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
