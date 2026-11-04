import React from "react";
import ReactDOM from "react-dom/client";
import AccessGate from "./AccessGate";
import "./styles.css";
import "./service-design.css";
import "./service-responsive.css";
import "./workspace-shell.css";
import "./ambient-motion.css";
import "./record-workspace.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AccessGate />
  </React.StrictMode>,
);
