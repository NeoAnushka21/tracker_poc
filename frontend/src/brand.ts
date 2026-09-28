/**
 * Product naming in one place (the names aren't final). To rename the app, change these,
 * then APP_NAME in backend/app/config.py, the persona line in backend/app/llm/prompt.py,
 * and public/favicon.svg. The page <title> and dev hostname come from here automatically.
 * - APP_NAME / APP_MARK: the app itself, used everywhere except inside the chat.
 * - BOT_NAME: the chat assistant, shown only in the Chat interface (with its avatar) and on the
 *   loading/wake screen (WakeScreen), where MacBro dances while the free server wakes.
 * - APP_DEV_HOST: local address. Any *.localhost name reaches this machine with no setup.
 * - APP_DOMAIN: the planned public domain, used once the app is deployed (not registered yet).
 */
export const APP_NAME = "OmniAI";
export const APP_MARK = "OAI";
export const BOT_NAME = "MacBro";
export const APP_DEV_HOST = "omniai.localhost";
export const APP_DOMAIN = "omniai.com";
