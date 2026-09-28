/**
 * The always-on launcher (a free Render static site, which never sleeps). It shows the dancing
 * MacBro while the app's free server wakes up, then opens the app, so visitors never see Render's
 * own "waking up" page. If the server is already awake, it opens the app almost instantly.
 * VITE_APP_URL is the app's address (set in render.yaml); empty means the same origin (dev).
 */
import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { DelayedWakeScreen, WakeScreen } from "./components/WakeScreen";
import { waitForServer } from "./wake";
import "@fontsource-variable/plus-jakarta-sans";
import "./styles.css";

const APP_URL = (import.meta.env.VITE_APP_URL ?? "").replace(/\/$/, "");
const GIVE_UP_AFTER_MS = 3 * 60 * 1000;

function Launcher() {
  const [stalled, setStalled] = useState(false);
  useEffect(() => {
    let cancelled = false;
    const giveUp = setTimeout(() => setStalled(true), GIVE_UP_AFTER_MS);
    waitForServer(APP_URL).then(() => {
      if (!cancelled) window.location.replace(`${APP_URL}/${window.location.hash}`);   // keeps #tab links
    });
    return () => { cancelled = true; clearTimeout(giveUp); };
  }, []);
  return stalled ? <WakeScreen stalled onRetry={() => window.location.reload()} /> : <DelayedWakeScreen />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Launcher />
  </StrictMode>,
);
