import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "@/app/App";
import { SessionProvider } from "@/state/sessionStore";
import "@/styles.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("No se encontro el nodo #root.");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <SessionProvider>
      <App />
    </SessionProvider>
  </React.StrictMode>,
);
