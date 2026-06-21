import React from "react";
import ReactDOM from "react-dom/client";
import BlockSequenceDemo from "./BlockSequenceDemo.jsx";
import "./styles.css";

// Presentation demo: voice + Lego block sequence + work-order unlock.
// The older full MPI dashboard (App.jsx, tool/6S panels) is kept in the repo but
// no longer rendered, so the demo shows only the clean block-sequence flow.
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BlockSequenceDemo />
  </React.StrictMode>
);
