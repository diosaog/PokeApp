import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppState } from "./state";
import App from "./App";
import "./design/tokens.css";
import "./styles.css";
import "./product.css";
import "./art-direction.css";
import "./product-polish.css";
import "./design/arena.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppState>
        <App />
      </AppState>
    </BrowserRouter>
  </React.StrictMode>,
);
