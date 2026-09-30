import { useState, type FormEvent } from "react";
import { api } from "../api";
import { APP_NAME } from "../brand";
import { AppLogo } from "./Avatar";
import ThemeToggle from "./ThemeToggle";

/** /reset-password#token=…: set a new password from the emailed link. The token is after "#",
 *  so it never reaches the server's logs; it's removed from the address bar once read. */
function readToken(): string {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
  if (token) window.history.replaceState(null, "", window.location.pathname);
  return token;
}

export default function ResetPasswordPage() {
  const [token] = useState(readToken);
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (next !== confirm) return setError("The passwords don't match.");
    setBusy(true);
    try {
      await api.resetPassword(token, next);
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center auth-page">
      <div className="auth-theme"><ThemeToggle /></div>
      <form className="card auth-card" onSubmit={submit}>
        <div className="auth-brand">
          <AppLogo size={56} />
          <div>
            <h1>Set a new password</h1>
            <p className="muted">{APP_NAME}</p>
          </div>
        </div>
        {done ? (
          <>
            <p className="ok" role="status">Your password is changed, and you've been signed out on every device.</p>
            <a className="button primary" href="/#login">Log in</a>
          </>
        ) : !token ? (
          <>
            <p className="error">This link is incomplete. Open the link from the email again, or ask for a new one.</p>
            <a href="/#login">← Back to log in</a>
          </>
        ) : (
          <>
            <label>New password <span className="muted">(at least 8 characters)</span>
              <input type="password" value={next} onChange={(e) => setNext(e.target.value)} minLength={8} required
                     autoFocus autoComplete="new-password" /></label>
            <label>Confirm new password
              <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={8} required
                     autoComplete="new-password" /></label>
            {error && <p className="error">{error}</p>}
            <button className="primary" disabled={busy}>{busy ? "Saving…" : "Set new password"}</button>
            <a className="small" href="/#login">← Back to log in</a>
          </>
        )}
      </form>
    </div>
  );
}
