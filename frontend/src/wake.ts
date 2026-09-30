/**
 * The free Render server sleeps after ~15 minutes idle and takes ~30–60 s to wake. While it's
 * waking, requests hang or get Render's own HTML page instead of our JSON. This module detects
 * that, tells the UI to show the WakeScreen, and waits until /api/health answers again.
 * The welcome page (welcome.ts) uses the same check against the app's address.
 */
import { useSyncExternalStore } from "react";

const PROBE_TIMEOUT_MS = 5000;
const POLL_EVERY_MS = 2000;
/** A request slower than this triggers a health check (chat replies are legitimately slow). */
export const SLOW_REQUEST_MS = 4000;

/** True when the server answers /api/health with our JSON. `base` is "" for the same origin. */
export async function serverAwake(base = ""): Promise<boolean> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), PROBE_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/api/health`, { signal: ctrl.signal, cache: "no-store" });
    if (!res.ok || !(res.headers.get("content-type") ?? "").includes("application/json")) return false;
    return (await res.json())?.ok === true;
  } catch {
    return false;   // network error, timeout, or no CORS header on Render's waking page
  } finally {
    clearTimeout(timer);
  }
}

/** Resolves once the server is awake (polls; each probe also nudges Render to wake it). */
export async function waitForServer(base = ""): Promise<void> {
  while (!(await serverAwake(base))) await new Promise((r) => setTimeout(r, POLL_EVERY_MS));
}

// --- "waking" flag shared with React ---------------------------------------------
let waking = false;
let pending: Promise<void> | null = null;
const listeners = new Set<() => void>();
const setWaking = (v: boolean) => { waking = v; listeners.forEach((l) => l()); };

/** Show the WakeScreen until the server is back. Concurrent callers share one wait. */
export function recoverServer(): Promise<void> {
  if (!pending) {
    setWaking(true);
    pending = waitForServer().finally(() => { pending = null; setWaking(false); });
  }
  return pending;
}

export function useServerWaking(): boolean {
  return useSyncExternalStore((l) => { listeners.add(l); return () => listeners.delete(l); }, () => waking);
}
