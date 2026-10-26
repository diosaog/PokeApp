import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppState } from "./state";
import App from "./App";
import { installPreferences } from "./preferences";
import { installSound } from "./sound";
import "@fontsource-variable/rubik/wght.css";
import "./design/tokens.css";
import "./styles.css";
import "./product.css";
import "./art-direction.css";
import "./product-polish.css";
import "./design/arena.css";
import "./design/evolution.css";
installPreferences();
installSound();
// First paint waits (at most 1.2 s) for the Rubik Latin face, so text never
// re-flows under the trainer once the font swaps in.
const fontReady = Promise.race([
  document.fonts?.load('700 1rem "Rubik Variable"') ?? Promise.resolve(),
  new Promise((resolve) => setTimeout(resolve, 1200)),
]).catch(() => undefined);
void fontReady.then(() =>
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <BrowserRouter>
        <AppState>
          <App />
        </AppState>
      </BrowserRouter>
    </React.StrictMode>,
  ),
);
