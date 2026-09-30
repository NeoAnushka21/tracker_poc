/**
 * The welcome page (welcome.html): what every visitor who isn't signed in sees first.
 * - On the app's own address it's served at /welcome (the app sends signed-out visitors here).
 * - On the always-on static site (render.yaml "omniai-app") it's the start page: the app's free
 *   server may be asleep, so this page starts waking it as soon as it opens (VITE_APP_URL is the
 *   app's address; empty = the same origin). Join / Log in go straight to the app's Create account /
 *   Log in page once it answers; before that the button shows a spinner and moves on by itself.
 * - Old links to an app tab (e.g. #dashboard on the static site) are forwarded into the app.
 */
import "@fontsource-variable/plus-jakarta-sans";
import "./welcome.css";
import { serverAwake, waitForServer } from "./wake";

const APP_URL = (import.meta.env.VITE_APP_URL ?? "").replace(/\/$/, "");
const SLIDE_MS = 5000;
const SLOW_WAKE_MS = 60_000;
/** In-page anchors; any other #hash is an app link (a tab, #login, #signup) to forward. */
const PAGE_ANCHORS = new Set(["", "#top", "#meet", "#ways", "#pantry", "#about", "#feedback"]);

// ---- wake the app in the background -------------------------------------------------
let ready = false;
const awake: Promise<void> = (async () => {
  if (!(await serverAwake(APP_URL))) await waitForServer(APP_URL);
  ready = true;
})();

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const status = $("status");
const statusTitle = $("status-title");
const statusText = $("status-text");
const spin = status.querySelector<HTMLElement>(".spinner")!;

function showStatus(title: string, text: string) {
  statusTitle.textContent = title;
  statusText.textContent = text;
  spin.hidden = false;
  status.hidden = false;
}

/** Go to the app (#signup, #login, or a forwarded tab), waiting for it to wake if needed. */
function openApp(hash: string, el?: HTMLElement) {
  const target = `${APP_URL}/${hash}`;
  if (ready) { window.location.assign(target); return; }
  if (el?.getAttribute("aria-busy") === "true") return;
  if (el) {
    el.setAttribute("aria-busy", "true");
    el.innerHTML = '<span class="spinner" aria-hidden="true"></span> Getting ready…';
  }
  showStatus("Getting Tandurust ready…", "This takes up to a minute the first time. You'll go straight in.");
  const slow = setTimeout(() => showStatus("Still waking up…", "Taking longer than usual. Keep this page open; it will continue by itself."), SLOW_WAKE_MS);
  void awake.then(() => { clearTimeout(slow); window.location.assign(target); });
}

// An old bookmark to an app tab (static site): forward it instead of showing the page.
if (!PAGE_ANCHORS.has(window.location.hash)) {
  showStatus("Opening Tandurust…", "One moment.");
  openApp(window.location.hash);
}

document.querySelectorAll<HTMLElement>("[data-go]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    openApp(el.dataset.go === "signup" ? "#signup" : "#login", el);
  });
});

// Privacy and Terms live in the app.
document.querySelectorAll<HTMLAnchorElement>("a[data-app-link]").forEach((a) => {
  a.href = `${APP_URL}${a.getAttribute("href")}`;
});

// ---- example chats: a slideshow of three tabs (click, arrow keys, Home/End) --------------
// Plays by itself (5 s a chat, looping); pauses on hover, on keyboard focus inside the card and when
// the card is off screen; the button pauses / plays; no autoplay with reduced motion.
const card = document.querySelector<HTMLElement>(".demo-card")!;
const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>('.demo [role="tab"]'));
const playBtn = $("play");
const playIcon = $("play-icon");
const count = $("slide-count");
const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let current = 0, progress = 0, last: number | null = null;
let userPaused = calm, hovered = false, focused = false, offscreen = false;

function select(i: number, focus: boolean) {
  current = (i + tabs.length) % tabs.length;
  progress = 0;
  tabs.forEach((t, k) => {
    const on = k === current;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    t.style.setProperty("--p", "0");
    const panel = document.getElementById(t.getAttribute("aria-controls")!)!;
    panel.classList.toggle("is-off", !on);
    if (on) panel.removeAttribute("inert"); else panel.setAttribute("inert", "");
  });
  count.textContent = `Example ${current + 1} of ${tabs.length}`;
  if (focus) tabs[current].focus();
}

const paused = () => userPaused || hovered || focused || offscreen;

function setPlayButton() {
  playBtn.setAttribute("aria-label", userPaused ? "Play the examples" : "Pause the examples");
  playBtn.title = userPaused ? "Play" : "Pause";
  playIcon.innerHTML = userPaused
    ? '<path d="M3 1.5v9l7.5-4.5z" fill="currentColor"/>'
    : '<rect x="2" y="1.5" width="2.8" height="9" rx="1" fill="currentColor"/><rect x="7.2" y="1.5" width="2.8" height="9" rx="1" fill="currentColor"/>';
}

function frame(now: number) {
  if (last !== null && !paused()) {
    progress += (now - last) / SLIDE_MS;
    if (progress >= 1) select(current + 1, false);
    tabs[current].style.setProperty("--p", String(Math.min(progress, 1)));
  }
  last = now;
  requestAnimationFrame(frame);
}

tabs.forEach((t, i) => {
  t.addEventListener("click", () => select(i, false));
  t.addEventListener("keydown", (e) => {
    const k = ({ ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 } as Record<string, number>)[e.key];
    if (k === undefined) return;
    e.preventDefault();
    select(k, true);
  });
});
playBtn.addEventListener("click", () => { userPaused = !userPaused; setPlayButton(); });
card.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") hovered = true; });
card.addEventListener("pointerleave", () => { hovered = false; });
card.addEventListener("focusin", (e) => { focused = e.target !== playBtn; });
card.addEventListener("focusout", () => { focused = false; });
if ("IntersectionObserver" in window) {
  new IntersectionObserver((entries) => { offscreen = !entries[0].isIntersecting; }, { threshold: 0.35 }).observe(card);
}
setPlayButton();
select(0, false);
requestAnimationFrame(frame);

// ---- feedback email: copy button (the clipboard may be refused: select the address instead) ----
const copyBtn = $("copy-mail");
const copyNote = $("copy-note");
copyBtn.addEventListener("click", () => {
  const done = () => {
    copyBtn.textContent = "Copied";
    copyNote.textContent = "Email address copied.";
    setTimeout(() => { copyBtn.textContent = "Copy"; }, 2000);
  };
  const fallback = () => {
    const range = document.createRange();
    range.selectNodeContents($("mail-link"));
    const sel = window.getSelection();
    sel?.removeAllRanges();
    sel?.addRange(range);
    copyNote.textContent = "Selected. Press Ctrl+C (or long-press) to copy.";
  };
  try { navigator.clipboard.writeText(copyBtn.dataset.email ?? "").then(done, fallback); } catch { fallback(); }
});
