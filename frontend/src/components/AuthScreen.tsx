import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";
import { AppLogo } from "./Avatar";
import { APP_NAME, APP_TAGLINE } from "../brand";
import ThemeToggle from "./ThemeToggle";
import GoogleButton from "./GoogleButton";

export default function AuthScreen({ onAuthed }: { onAuthed: (u: User) => void }) {
  const [mode, setMode] = useState<"login" | "register" | "admin" | "forgot">("login");
  const [resetAvailable, setResetAvailable] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);   // e.g. "a reset link is on its way"
  const [needCode, setNeedCode] = useState(false);   // admin with two-step sign-in on
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [consentText, setConsentText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);
  // A Google sign-in waiting for the user's OK: link to an existing email account, or consent for a new one.
  const [pending, setPending] = useState<{ credential: string; kind: "link" | "consent"; email: string } | null>(null);
  const [pendingConsent, setPendingConsent] = useState(false);

  useEffect(() => {
    api.consentText().then((c) => setConsentText(c.text)).catch(() => setConsentText(null));
    api.authOptions()
      .then((o) => { setGoogleClientId(o.google_client_id); setResetAvailable(o.password_reset); })
      .catch(() => setGoogleClientId(null));
  }, []);

  async function google(credential: string, flags: { consent?: boolean; link?: boolean } = {}) {
    setError(null);
    setBusy(true);
    try {
      const r = await api.googleLogin(credential, flags);
      if (r.status === "ok") return onAuthed(r.user);
      setPendingConsent(mode === "register" && consent);
      setPending({ credential, kind: r.status === "link_required" ? "link" : "consent", email: r.email });
    } catch (err) {
      setError((err as Error).message);
      setPending(null);
    } finally {
      setBusy(false);
    }
  }

  if (pending) {
    const linking = pending.kind === "link";
    return (
      <div className="center auth-page">
        <div className="auth-theme"><ThemeToggle /></div>
        <div className="card auth-card">
          <div className="auth-brand">
            <AppLogo size={56} />
            <div>
              <h1>{linking ? "Link your Google account?" : `Welcome to ${APP_NAME}`}</h1>
              <p className="muted">{pending.email}</p>
            </div>
          </div>
          {linking ? (
            <p>
              You already have a {APP_NAME} account with this email. Link Google to it and you can log in with
              either Google or your password. Your data stays as it is.
            </p>
          ) : (
            <>
              <p>Create your {APP_NAME} account with this Google account.</p>
              <label className="consent-box">
                <input type="checkbox" checked={pendingConsent} onChange={(e) => setPendingConsent(e.target.checked)} />
                <span>{consentText ?? "I agree that the data I share is used for my recommendations and to develop the app."}</span>
              </label>
              <p className="muted small auth-legal">
                For adults 18 and over. <a href="/privacy" target="_blank" rel="noopener">Privacy</a> · <a href="/terms" target="_blank" rel="noopener">Terms</a>
              </p>
            </>
          )}
          {error && <p className="error">{error}</p>}
          <button className="primary" disabled={busy || (!linking && !pendingConsent)}
                  onClick={() => google(pending.credential, linking ? { link: true } : { consent: true })}>
            {busy ? "…" : linking ? "Link and continue" : "Create account"}
          </button>
          <button type="button" className="ghost" disabled={busy} onClick={() => { setPending(null); setError(null); }}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "forgot") {
      setBusy(true);
      try {
        setNotice((await api.forgotPassword(email)).message);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setBusy(false);
      }
      return;
    }
    if (mode === "register" && !consent) {
      setError("Please tick the consent box to create an account.");
      return;
    }
    setBusy(true);
    try {
      const user = mode === "login" ? await api.login(email, password)
        : mode === "admin" ? await api.adminLogin(email, password, code)
        : await api.register(email, password, consent);
      onAuthed(user);
    } catch (err) {
      const message = (err as Error).message;
      if (mode === "admin" && message === "code_required") {
        setNeedCode(true);
        setError(null);
      } else {
        setError(message);
      }
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
            <p className="app-tagline">{APP_TAGLINE}</p>
            <p className="muted">
              {mode === "admin" ? "Admin console login. For the app's administrators only."
                : mode === "forgot" ? "Forgot your password? We'll email you a link to set a new one."
                : "Track calories and macros just by chatting about what you ate."}
            </p>
          </div>
        </div>
        {mode !== "admin" && mode !== "forgot" && (
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
        {mode !== "forgot" && (
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
        )}
        {mode === "admin" && needCode && (
          <label>
            6-digit code from your authenticator app
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code"
                   pattern="[0-9 ]{6,7}" maxLength={7} required autoFocus />
          </label>
        )}
        {mode === "login" && resetAvailable && (
          <button type="button" className="link forgot-link"
                  onClick={() => { setMode("forgot"); setError(null); setNotice(null); }}>
            Forgot password?
          </button>
        )}

        {mode === "forgot" ? (
          notice && <p className="ok small" role="status">{notice}</p>
        ) : mode === "register" ? (
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

        {mode !== "admin" && mode !== "forgot" && (
          <p className="muted small auth-legal">
            For adults 18 and over. Estimates, not medical advice.{" "}
            <a href="/privacy" target="_blank" rel="noopener">Privacy</a> · <a href="/terms" target="_blank" rel="noopener">Terms</a>
          </p>
        )}
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy || (mode === "register" && !consent)}>
          {busy ? "…" : mode === "login" ? "Log in" : mode === "admin" ? "Log in as admin"
            : mode === "forgot" ? "Send reset link" : "Create account"}
        </button>
        {mode !== "admin" && mode !== "forgot" && googleClientId && (
          <>
            <div className="auth-or" aria-hidden="true"><span>or</span></div>
            <GoogleButton clientId={googleClientId}
                          onCredential={(c) => google(c, mode === "register" && consent ? { consent: true } : {})}
                          onError={setError} />
          </>
        )}
        {mode === "forgot" ? (
          <button type="button" className="link admin-link" onClick={() => { setMode("login"); setError(null); }}>
            ← Back to log in
          </button>
        ) : (
          <button type="button" className="link admin-link" onClick={() => { setMode(mode === "admin" ? "login" : "admin"); setError(null); }}>
            {mode === "admin" ? "← Back to user login" : "Admin login"}
          </button>
        )}
      </form>
    </div>
  );
}
