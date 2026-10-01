/**
 * The welcome page (welcome.html): what every visitor who isn't signed in sees first.
 * - On the app's own address it's served at /welcome (the app sends signed-out visitors here).
 * - On the always-on static site (render.yaml "tandurust-app") it's the start page: the app's free
 *   server may be asleep, so this page starts waking it as soon as it opens (VITE_APP_URL is the
 *   app's address; empty = the same origin). Join / Log in go straight to the app's Create account /
 *   Log in page once it answers; before that the button shows a spinner and moves on by itself.
 * - Old links to an app tab (e.g. #dashboard on the static site) are forwarded into the app.
 * - Join depends on the server's JOIN_MODE (GET /api/waitlist/options): "open" goes to Create account,
 *   "waitlist" opens the "Join the waitlist" form (POST /api/waitlist). #join opens the form directly.
 * - The Demo section (#demo) is a step-by-step tour of example screens.
 */
import "@fontsource-variable/plus-jakarta-sans";
import "./welcome.css";
import { serverAwake, waitForServer } from "./wake";

const APP_URL = (import.meta.env.VITE_APP_URL ?? "").replace(/\/$/, "");
const SLIDE_MS = 5000;
const SLOW_WAKE_MS = 60_000;
/** In-page anchors; any other #hash is an app link (a tab, #login, #signup) to forward. */
const PAGE_ANCHORS = new Set(["", "#top", "#demo", "#join", "#for", "#meet", "#ways", "#pantry", "#about", "#feedback"]);
const JOIN_MODE_KEY = "tandurust.joinMode";   // last known mode, so a returning visitor's Join doesn't wait

type JoinMode = "open" | "waitlist";

// ---- wake the app in the background -------------------------------------------------
let ready = false;
const awake: Promise<void> = (async () => {
  if (!(await serverAwake(APP_URL))) await waitForServer(APP_URL);
  ready = true;
})();

/** What Join does. Asked once the server is awake. If the answer can't be read, assume invite-only: the page
 *  must never promise direct access that the server would then refuse. */
const joinModeReady: Promise<JoinMode> = awake
  .then(() => fetch(`${APP_URL}/api/waitlist/options`, { cache: "no-store" }))
  .then((r) => (r.ok ? r.json() : { join_mode: "waitlist" }))
  .then((o: { join_mode?: string }): JoinMode => (o.join_mode === "open" ? "open" : "waitlist"))
  .catch((): JoinMode => "waitlist");
let joinMode: JoinMode | null = null;
try {
  const saved = localStorage.getItem(JOIN_MODE_KEY);
  if (saved === "open" || saved === "waitlist") { joinMode = saved; document.documentElement.dataset.join = saved; }
} catch { /* storage blocked: ask the server */ }
void joinModeReady.then((m) => {
  joinMode = m;
  document.documentElement.dataset.join = m;   // which wording shows: invite-only or open sign-up (welcome.css)
  try { localStorage.setItem(JOIN_MODE_KEY, m); } catch { /* fine without it */ }
});

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

/** Join: Create account while sign-up is open, the "Join the waitlist" form while it's by invitation.
 *  The mode is known once the server answers; until then the button waits, like Log in. */
function join(el?: HTMLElement) {
  if (joinMode === "waitlist") { openJoinForm(); return; }
  if (joinMode === "open") { openApp("#signup", el); return; }
  if (el?.getAttribute("aria-busy") === "true") return;
  const label = el?.innerHTML;
  if (el) {
    el.setAttribute("aria-busy", "true");
    el.innerHTML = '<span class="spinner" aria-hidden="true"></span> Getting ready…';
  }
  showStatus("Getting Tandurust ready…", "This takes up to a minute the first time.");
  void joinModeReady.then((m) => {
    if (m === "open") { window.location.assign(`${APP_URL}/#signup`); return; }
    status.hidden = true;
    if (el) { el.removeAttribute("aria-busy"); el.innerHTML = label ?? "Join"; }
    openJoinForm();
  });
}

document.querySelectorAll<HTMLElement>("[data-go]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    if (el.dataset.go === "signup") join(el);
    else openApp("#login", el);
  });
});

// Privacy and Terms (/privacy, /terms) are relative links: both the app and the always-on welcome site
// publish their pre-rendered pages (render.yaml), so Google's brand check finds them on the home page's domain.

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

// ---- demo: a step-by-step tour (click a step, arrow keys, Home/End, Back / Next) ----------------
const stops = Array.from(document.querySelectorAll<HTMLButtonElement>('.tour-steps [role="tab"]'));
const tourPrev = $<HTMLButtonElement>("tour-prev");
const tourNext = $<HTMLButtonElement>("tour-next");
const tourCount = $("tour-count");
const stepRow = document.querySelector<HTMLElement>(".tour-steps")!;
let stop = 0;

function showStop(i: number, focus: boolean) {
  stop = Math.max(0, Math.min(i, stops.length - 1));
  stops.forEach((t, k) => {
    const on = k === stop;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    const panel = document.getElementById(t.getAttribute("aria-controls")!)!;
    panel.classList.toggle("is-off", !on);
    if (on) panel.removeAttribute("inert"); else panel.setAttribute("inert", "");
  });
  // On phones the steps are one scrolling row: bring the current one into view (the row only, not the page).
  const b = stops[stop];
  stepRow.scrollTo({ left: b.offsetLeft - (stepRow.clientWidth - b.offsetWidth) / 2, behavior: "smooth" });
  tourCount.textContent = `Stop ${stop + 1} of ${stops.length}`;
  tourPrev.disabled = stop === 0;
  const next = stops[stop + 1]?.querySelector("b")?.textContent;
  tourNext.textContent = next ? `Next: ${next} ›` : "Start again ›";
  if (focus) b.focus();
}

stops.forEach((t, i) => {
  t.addEventListener("click", () => showStop(i, false));
  t.addEventListener("keydown", (e) => {
    const keys: Record<string, number> = { ArrowDown: i + 1, ArrowRight: i + 1, ArrowUp: i - 1, ArrowLeft: i - 1, Home: 0, End: stops.length - 1 };
    const k = keys[e.key];
    if (k === undefined) return;
    e.preventDefault();
    showStop(k, true);
  });
});
tourPrev.addEventListener("click", () => showStop(stop - 1, false));
tourNext.addEventListener("click", () => showStop(stop + 1 < stops.length ? stop + 1 : 0, false));
showStop(0, false);

// ---- "Join the waitlist" form (JOIN_MODE=waitlist) ------------------------------------------
const dialog = $<HTMLDialogElement>("join-dialog");
const form = $<HTMLFormElement>("join-form");
const fields = $("join-fields");
const done = $("join-done");
const joinError = $("join-error");
const submitBtn = $<HTMLButtonElement>("join-submit");
const field = (id: string) => $<HTMLInputElement>(id);

function openJoinForm() {
  if (dialog.open) return;
  joinError.hidden = true;
  dialog.showModal();
  if (done.hidden) field("join-name").focus(); else done.focus();
}

function clearJoinHash() {
  if (window.location.hash === "#join") history.replaceState(null, "", window.location.pathname + window.location.search);
}

function closeJoinForm() {
  dialog.close();
  clearJoinHash();
}

function fail(message: string, input?: HTMLInputElement) {
  joinError.textContent = message;
  joinError.hidden = false;
  if (input) { input.setAttribute("aria-invalid", "true"); input.focus(); }
}

/** FastAPI errors: {detail: "text"} or, for invalid fields, {detail: [{msg: "Value error, ..."}]}. */
function errorText(body: unknown): string | null {
  const d = (body as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, "");
  return null;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (submitBtn.getAttribute("aria-busy") === "true") return;
  joinError.hidden = true;
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
  const name = field("join-name"), email = field("join-email"), consent = field("join-consent");
  if (!name.value.trim()) return fail("Please enter your name.", name);
  if (!email.value.trim() || !email.checkValidity()) return fail("Please enter a valid email address.", email);
  if (!consent.checked) return fail("Please tick the box so we may email you about access.", consent);

  submitBtn.setAttribute("aria-busy", "true");
  submitBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Sending…';
  const slow = setTimeout(() => {
    submitBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Waking the server, up to a minute…';
  }, 4000);
  try {
    await awake;
    const r = await fetch(`${APP_URL}/api/waitlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name.value, email: email.value, interest: field("join-interest").value || null,
        consent: true, website: field("join-website").value,
      }),
    });
    const body: unknown = await r.json().catch(() => null);
    if (!r.ok) { fail(errorText(body) ?? "Something went wrong. Please try again in a moment."); return; }
    $("join-done-title").textContent = `You're on the list, ${name.value.trim().split(" ")[0]}!`;
    $("join-done-text").textContent = `We'll email your invitation to ${email.value.trim()} as soon as there's a spot. Check your spam folder too.`;
    fields.hidden = true;
    done.hidden = false;
    done.focus();
  } catch {
    fail("We couldn't reach Tandurust. Check your connection and try again.");
  } finally {
    clearTimeout(slow);
    submitBtn.removeAttribute("aria-busy");
    submitBtn.textContent = "Join the waitlist";
  }
});

$("join-close").addEventListener("click", closeJoinForm);
$("join-done-close").addEventListener("click", closeJoinForm);
$("join-done-demo").addEventListener("click", closeJoinForm);        // then the link scrolls to #demo
dialog.addEventListener("click", (e) => { if (e.target === dialog) closeJoinForm(); });   // the backdrop
dialog.addEventListener("cancel", clearJoinHash);                    // Escape

// A shared link straight to the form: /welcome#join (or the static site's /#join).
if (window.location.hash === "#join") openJoinForm();
