import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { WakeScreen } from "./components/WakeScreen";
import { useServerWaking } from "./wake";
import "@fontsource-variable/plus-jakarta-sans";
import "./styles.css";

/** Covers any screen while a request waits for the sleeping server to wake (see wake.ts). */
function WakeOverlay() {
  return useServerWaking() ? <WakeScreen overlay /> : null;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
    <WakeOverlay />
  </StrictMode>,
);
