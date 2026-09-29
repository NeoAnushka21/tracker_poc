import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import PrivacyPage from "./components/PrivacyPage";
import ResetPasswordPage from "./components/ResetPasswordPage";
import TermsPage from "./components/TermsPage";
import { WakeScreen } from "./components/WakeScreen";
import { useServerWaking } from "./wake";
import "@fontsource-variable/plus-jakarta-sans";
import "./styles.css";

/** Covers any screen while a request waits for the sleeping server to wake (see wake.ts). */
function WakeOverlay() {
  return useServerWaking() ? <WakeScreen overlay /> : null;
}

const page = window.location.pathname.replace(/\/$/, "");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* Public pages that work without signing in (the server returns index.html for any non-API path). */}
    {page === "/privacy" ? <PrivacyPage /> : page === "/terms" ? <TermsPage />
      : page === "/reset-password" ? <ResetPasswordPage /> : <App />}
    <WakeOverlay />
  </StrictMode>,
);
