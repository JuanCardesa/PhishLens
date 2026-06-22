import React from "react";
import { createRoot } from "react-dom/client";

import { ErrorBoundary } from "./ErrorBoundary";
import { Popup } from "./Popup";

const root = document.getElementById("root");

if (root) {
  createRoot(root).render(
    <React.StrictMode>
      <ErrorBoundary>
        <Popup />
      </ErrorBoundary>
    </React.StrictMode>,
  );
}
