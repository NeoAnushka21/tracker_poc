import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";
import { AppLogo } from "./Avatar";
import { APP_NAME } from "../brand";
import ThemeToggle from "./ThemeToggle";

export default function AuthScreen({ onAuthed }: { onAuthed: (u: User) => void }) {
  const [mode, setMode] = useState<"login" | "register" | "admin">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [consentText, setConsentText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.consentText().then((c) => setConsentText(c.text)).catch(() => setConsentText(null));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "register" && !consent) {
      setError("Please tick the consent box to create an account.");
      return;
    }
    setBusy(true);
    try {
      const user = mode === "login" ? await api.login(email, password)
        : mode === "admin" ? await api.adminLogin(email, password)
        : await api.register(email, password, consent);
      onAuthed(user);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center auth-page">
      <div className="auth-theme"><ThemeToggle /></div>
      <form className={`card auth-card ${mode === "admin" ? "admin-auth" : ""}`} onSubmit={submit}>
        <div className="auth-brand">
          <AppLogo size={72} />
          <div>
            <h1>{APP_NAME}{mode === "admin" && <span className="admin-badge">Admin</span>}</h1>
            <p className="muted">
              {mode === "admin" ? "Admin console login. For the app's administrators only."
                : "Track calories and macros just by chatting about what you ate."}
            </p>
          </div>
        </div>
        {mode !== "admin" && (
          <div className="segmented auth-modes" role="tablist" aria-label="Account">
            <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "on" : ""}
                    onClick={() => { setMode("login"); setError(null); }}>Log in</button>
            <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "on" : ""}
                    onClick={() => { setMode("register"); setError(null); }}>Create account</button>
          </div>
        )}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </label>

        {mode === "register" ? (
          <label className="consent-box">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
            <span>{consentText ?? "I agree that the data I share is used for my recommendations and to develop the app."}</span>
          </label>
        ) : mode === "admin" ? null : (
          <p className="consent-note muted small">
            By logging in, you agree that the data you share with {APP_NAME} is used for your recommendations and to
            improve the application, and that chat messages are processed by third-party AI services.
          </p>
        )}

        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy || (mode === "register" && !consent)}>
          {busy ? "…" : mode === "login" ? "Log in" : mode === "admin" ? "Log in as admin" : "Create account"}
        </button>
        <button type="button" className="link admin-link" onClick={() => { setMode(mode === "admin" ? "login" : "admin"); setError(null); }}>
          {mode === "admin" ? "← Back to user login" : "Admin login"}
        </button>
      </form>
    </div>
  );
}
