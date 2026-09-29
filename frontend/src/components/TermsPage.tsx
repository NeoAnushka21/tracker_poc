import { APP_NAME, PRIVACY_CONTACT } from "../brand";
import { AppLogo } from "./Avatar";
import ThemeToggle from "./ThemeToggle";

const UPDATED = "29 September 2026";

/** Public terms of use at /terms (no login needed). Plain language; the owner reviews it before a
 *  public launch. Keep it consistent with the privacy page and what the app really does. */
export default function TermsPage() {
  return (
    <div className="privacy-page">
      <div className="auth-theme"><ThemeToggle /></div>
      <article className="card privacy-card">
        <header className="privacy-head">
          <AppLogo size={48} />
          <div>
            <h1>Terms of use</h1>
            <p className="muted small">Last updated {UPDATED}</p>
          </div>
        </header>

        <p>
          {APP_NAME} is a free calorie and macro tracker, run as a small personal project and still in development.
          By creating an account or using it, you agree to these terms. How we handle your data is on the{" "}
          <a href="/privacy">privacy page</a>.
        </p>

        <h2>Who can use it</h2>
        <ul>
          <li>You need to be 18 or over.</li>
          <li>One account per person. Keep your password to yourself; you're responsible for what happens in your account.</li>
        </ul>

        <h2>What it is, and isn't</h2>
        <ul>
          <li>Calories, nutrients, targets, BMI and body-fat numbers are <b>estimates</b>, some made by AI. They can be wrong. Check anything important.</li>
          <li>It's <b>not medical advice</b> and not a substitute for a doctor or dietitian, especially for medical conditions, pregnancy, eating disorders or big changes to how you eat.</li>
          <li>Nothing the assistant suggests is saved until you press the button to confirm it.</li>
        </ul>

        <h2>Fair use</h2>
        <ul>
          <li>The AI runs on a free service shared by everyone, so each account has a daily number of AI messages.</li>
          <li>Don't try to break, overload or get around the app's limits or security, use it with automated tools, or access other people's data.</li>
          <li>Don't use it for anything illegal or to harm others.</li>
        </ul>
        <p>We may pause or close accounts that break these rules.</p>

        <h2>Your content</h2>
        <p>
          What you log stays yours. You let us store and process it to run the app and to improve it, as the privacy page
          describes. You can download or delete it at any time in Settings.
        </p>

        <h2>The service</h2>
        <ul>
          <li>It's provided free and "as is". It may be slow (the free server naps when idle), have mistakes, or be unavailable at times.</li>
          <li>Features may change, and we may stop the service. If we do, we'll try to give notice so you can download your data.</li>
          <li>As far as the law allows, we aren't liable for losses from using the app or relying on its estimates.</li>
        </ul>

        <h2>Changes</h2>
        <p>We may update these terms. If a change matters, we'll tell you in the app.</p>

        <h2>Contact</h2>
        <p>Questions: <a href={`mailto:${PRIVACY_CONTACT}`}>{PRIVACY_CONTACT}</a>.</p>

        <p className="privacy-back"><a href="/">← Back to {APP_NAME}</a></p>
      </article>
    </div>
  );
}
