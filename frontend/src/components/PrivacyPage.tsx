import { APP_NAME, PRIVACY_CONTACT } from "../brand";
import { AppLogo } from "./Avatar";
import ThemeToggle from "./ThemeToggle";

const UPDATED = "1 October 2026";

/** Public privacy notice at /privacy (no login needed). Keep it in step with what the app really does:
 *  the consent text (backend config.py), the export (services/export.py) and deletion (services/accounts.py). */
export default function PrivacyPage() {
  return (
    <div className="privacy-page">
      <div className="auth-theme"><ThemeToggle /></div>
      <article className="card privacy-card">
        <header className="privacy-head">
          <AppLogo size={48} />
          <div>
            <h1>Privacy at {APP_NAME}</h1>
            <p className="muted small">Last updated {UPDATED}</p>
          </div>
        </header>

        <p>
          {APP_NAME} is a free calorie and macro tracker, run as a small personal project and still in development.
          This page explains in plain words what we store, why, who else handles it, and what you can do about it.
        </p>

        <h2>What we store</h2>
        <ul>
          <li><b>Account:</b> your email, and either a scrambled (hashed) password or a link to your Google account. We never see your Google password.</li>
          <li><b>Profile:</b> name (optional), date of birth (your age is worked out from it), sex, height, weight, goal, activity level, country and region (optional), time zone, units.</li>
          <li><b>About you (optional, only if you fill it in):</b> diet type, allergies and intolerances, weight-change pace, usual meal times, training days and type. <b>Health details</b> (health conditions, pregnancy or breastfeeding) are stored only after you tick a separate box agreeing to it; they're used only to set your targets and to give MacBro context, and are sent with your chat messages to the AI service. Remove them any time in Settings → About you.</li>
          <li><b>What you log:</b> meals and their nutrients, water, saved foods and recipes, targets, body measurements.</li>
          <li><b>Chat:</b> your messages and the assistant's replies, and the suggestions you confirmed or cancelled.</li>
          <li><b>Usage:</b> when you sign in, how many AI requests you made each day, and technical details of each AI call (model, size, timing), used to share the free AI allowance fairly.</li>
          <li><b>Waitlist (only if you use "Join the waitlist" on the welcome page):</b> your name, email, what you'd like to track (optional), and when you joined and were let in. It's used only to email you about access and to plan how many people we can let in. Write to us to be taken off the list; deleting your account also removes it.</li>
          <li><b>On your device:</b> one sign-in cookie (needed to keep you logged in) and your light/dark theme choice. No advertising or tracking cookies, and no analytics.</li>
          <li><b>Camera and photos:</b> only when you scan a packaged product. The camera picture or photo is read on your device for its barcode and is never uploaded or stored; only the barcode number is searched (see Open Food Facts below).</li>
        </ul>

        <h2>Why</h2>
        <ul>
          <li>To run the tracker: work out your targets, estimate nutrition, show your history and trends.</li>
          <li>To improve and develop the app, as described in the consent you gave when you signed up.</li>
          <li>To keep it working and safe: daily AI limits, sign-in attempt limits, fixing problems.</li>
        </ul>
        <p>We don't sell your data or use it for advertising.</p>

        <h2>Who else handles it</h2>
        <ul>
          <li><b>Render</b> (Singapore) runs the app, and <b>Neon</b> (Singapore) hosts the database.</li>
          <li><b>Groq</b> (United States) runs the open-source AI models. To answer a chat message it receives that message with related context: your name if you set one, goal, weight, targets, today's or the picked day's logs, and matching saved foods. It doesn't receive your email or password. Groq doesn't keep it by default; under its terms it may keep logs for up to 30 days, only to fix errors or investigate abuse.</li>
          <li><b>Google</b>, only if you use Continue with Google: Google tells us your email, that it's verified, and your name. Google's sign-in button follows Google's own privacy and cookie rules.</li>
          <li><b>Brevo</b> sends our emails: password-reset links when you ask for one, and waitlist invitations. It receives your email address and the email's text (for a waitlist sign-up, the administrator's alert also contains your name and what you'd like to track).</li>
          <li><b>Open Food Facts</b> (a non-profit open food database, France), to find a packaged product's pack label: when you log a branded food in the chat, scan a pack, or search for a label in My Foods, our server sends it the product's brand and name or its barcode. It receives nothing about you: no name, email, photos or logs.</li>
          <li><b>Error reports:</b> if error reporting is switched on, <b>Sentry</b> receives technical reports when something breaks (the error and where in the code it happened). They don't include your chat messages, food logs, cookies or IP address. An uptime service also checks every few minutes that the app answers; it sees no personal data.</li>
          <li><b>The app's administrator</b> can view account data read-only, for support and development. Every such view is recorded, and it's included when you download your data.</li>
        </ul>

        <h2>How long we keep it</h2>
        <p>
          Until you delete your account. Deleting it removes your profile, logs, foods, chat and everything else linked to you.
          Two things stay, no longer linked to you: counts of AI model calls (for managing the free quota) and the record that an
          administrator viewed an account. The database provider keeps short-term backups for recovery, which expire on their own.
        </p>

        <h2>Your choices and rights</h2>
        <ul>
          <li><b>See your data:</b> Settings → Account &amp; privacy → <b>Download my data</b> gives you everything as a file.</li>
          <li><b>Correct it:</b> edit your profile, targets, logs and saved foods in the app.</li>
          <li><b>Delete it:</b> Settings → <b>Delete account</b> removes it permanently.</li>
          <li><b>Withdraw consent:</b> the app needs your consent to work, so withdrawing it means deleting your account.</li>
          <li><b>Questions or complaints:</b> email <a href={`mailto:${PRIVACY_CONTACT}`}>{PRIVACY_CONTACT}</a>.</li>
        </ul>

        <h2>Adults only</h2>
        <p>{APP_NAME} is for people aged 18 and over. We don't knowingly keep data about anyone younger.</p>

        <h2 id="health">Health information</h2>
        <p>
          Calorie, nutrient, BMI and body-fat numbers are estimates to help you track, not medical advice.
          Talk to a doctor or dietitian about medical conditions, pregnancy, or big changes to how you eat.
        </p>

        <h2>Changes</h2>
        <p>If we change how your data is used, we'll update this page and ask for your consent again in the app.</p>

        <p className="privacy-back"><a href="/terms">Terms of use</a> · <a href="/">← Back to {APP_NAME}</a></p>
      </article>
    </div>
  );
}
