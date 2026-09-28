import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";
import { MacBroAvatar } from "./Avatar";
import ThemeToggle from "./ThemeToggle";

export default function AuthScreen({ onAuthed }: { onAuthed: (u: User) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
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
      const user = mode === "login" ? await api.login(email, password) : await api.register(email, password, consent);
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
      <form className="card auth-card" onSubmit={submit}>
        <div className="auth-brand">
          <MacBroAvatar size={72} />
          <div>
            <h1>MacBro</h1>
            <p className="muted">Your macro bro. Log food by just telling me what you ate.</p>
          </div>
        </div>
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
        ) : (
          <p className="consent-note muted small">
            By logging in, you agree that the data you share with MacBro is used for your recommendations and to
            improve the application.
          </p>
        )}

        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy || (mode === "register" && !consent)}>
          {busy ? "…" : mode === "login" ? "Log in" : "Create account"}
        </button>
        <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
          {mode === "login" ? "New here? Create an account" : "Already have an account? Log in"}
        </button>
      </form>
    </div>
  );
}
