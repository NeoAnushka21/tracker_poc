/**
 * Product naming in one place. To rename the app, change these, then APP_NAME in
 * backend/app/config.py. The logo files are in public/brand/ (made from docs/brand/). The page <title>, the persona line in
 * backend/app/llm/prompt.py and the dev hostname come from here / config automatically.
 * Renamed OmniAI → Tandurust on 2026-09-30, for display only: the hostnames below, the Render
 * services, the live URL (omniai-hkv2.onrender.com), Google sign-in and internal ids stay "omniai".
 * - APP_NAME / APP_LOGO / APP_TAGLINE: the app itself, used everywhere except inside the chat.
 * - BOT_NAME: the chat assistant, shown only in the chat (the chat window, its minimized bubble and
 *   the Home invite that opens it, with its avatar) and on the loading/wake screen (WakeScreen),
 *   where MacBro dances while the free server wakes.
 * - APP_DEV_HOST: local address. Any *.localhost name reaches this machine with no setup.
 * - APP_DOMAIN: the planned public domain, used once the app is deployed (not registered yet).
 */
export const APP_NAME = "Tandurust";
/** The emblem (leaf + runner), transparent PNG, 1x and 2x (docs/brand/README.md). */
export const APP_LOGO = { src: "/brand/emblem-96.png", src2x: "/brand/emblem-192.png" };
export const APP_TAGLINE = "AI meal & wellness tracker";
export const BOT_NAME = "MacBro";
export const APP_DEV_HOST = "omniai.localhost";   // not renamed (display-only rename)
export const APP_DOMAIN = "omniai.com";          // not renamed (display-only rename)
/** Where people send privacy questions and requests (shown on /privacy). */
export const PRIVACY_CONTACT = "mhatre.anushka.work@gmail.com";
