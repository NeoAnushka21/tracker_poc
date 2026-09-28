import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";
import { GOALS } from "../format";
import TargetsEditor from "./TargetsEditor";
import ThemeToggle from "./ThemeToggle";
import { UserAvatar } from "./Avatar";

const LB_PER_KG = 2.20462;

type Section = "account" | "targets" | "security" | "delete";

type Props = {
  user: User;
  onClose: () => void;
  onSaved: (u: User) => void;
  onDeleted: () => void;
};

function when(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function AccountSection({ user }: { user: User }) {
  return (
    <>
      <div className="account-card">
        <UserAvatar name={user.preferred_name} email={user.email} size={48} />
        <div>
          <div className="account-name">{user.preferred_name ?? (user.is_admin ? "Administrator" : "No preferred name")}</div>
          <div className="muted">{user.email}</div>
        </div>
      </div>
      <dl className="settings-facts">
        <div><dt>Email</dt><dd>{user.email}</dd></div>
        <div><dt>Registered</dt><dd>{when(user.created_at)}</dd></div>
        <div><dt>Last login</dt><dd>{when(user.last_login_at)}</dd></div>
        <div><dt>Data consent given</dt><dd>{when(user.consented_at)}</dd></div>
        {!user.is_admin && (
          <>
            <div><dt>Goal</dt><dd>{user.goal_type ? GOALS[user.goal_type] ?? user.goal_type : "–"}</dd></div>
            <div><dt>Time zone</dt><dd>{user.timezone}</dd></div>
          </>
        )}
      </dl>
      <h3>Appearance</h3>
      <ThemeToggle />
    </>
  );
}

function TargetsSection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const imperial = user.unit_system === "imperial";
  const [weight, setWeight] = useState("");
  const [recalc, setRecalc] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const shownWeight = user.weight_kg == null ? "–"
    : imperial ? `${Math.round(user.weight_kg * LB_PER_KG * 10) / 10} lb` : `${user.weight_kg} kg`;

  async function saveWeight(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const kg = imperial ? Number(weight) / LB_PER_KG : Number(weight);
      onSaved(await api.logWeight(Math.round(kg * 10) / 10, recalc));
      setWeight("");
      setMsg(recalc ? "Weight saved and targets recalculated." : "Weight saved.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <>
      <h3 className="first">Daily targets</h3>
      <TargetsEditor
        key={`${user.targets?.effective_date}-${user.targets?.calories}-${user.targets?.protein_g}`}
        user={user}
        saveLabel="Save targets"
        onSaved={(u) => { onSaved(u); setMsg("Targets saved."); }}
      />
      <h3>Update weight</h3>
      <p className="muted small">Current: {shownWeight}</p>
      <form onSubmit={saveWeight} className="weight-form">
        <input type="number" step="0.1" min={20} max={900} value={weight} onChange={(e) => setWeight(e.target.value)}
               placeholder={imperial ? "lb" : "kg"} required />
        <label className="check">
          <input type="checkbox" checked={recalc} onChange={(e) => setRecalc(e.target.checked)} />
          Recalculate targets from new weight
        </label>
        <button className="primary">Save weight</button>
      </form>
      {msg && <p className="ok small">{msg}</p>}
      {error && <p className="error">{error}</p>}
    </>
  );
}

function SecuritySection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (next !== confirm) return setError("The new passwords don't match.");
    setBusy(true);
    try {
      await api.changePassword(current, next);
      setMsg("Password changed.");
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="settings-form">
      <h3 className="first">Change password</h3>
      <label>Current password<input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" /></label>
      <label>New password <span className="muted">(at least 8 characters)</span>
        <input type="password" value={next} onChange={(e) => setNext(e.target.value)} minLength={8} required autoComplete="new-password" /></label>
      <label>Confirm new password<input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={8} required autoComplete="new-password" /></label>
      {error && <p className="error">{error}</p>}
      {msg && <p className="ok small">{msg}</p>}
      <button className="primary" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
    </form>
  );
}

function DeleteSection({ user, onDeleted }: { user: User; onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.deleteAccount(password);
      onDeleted();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="settings-form danger-zone">
      <h3 className="first">Delete account</h3>
      <p>
        This permanently deletes your account and everything in it: food logs, saved foods and recipes, water logs,
        weight history, targets and your chats with MacBro. <b>This can't be undone.</b>
      </p>
      <label>Type <b>DELETE</b> to confirm<input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" /></label>
      <label>Your password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
      {error && <p className="error">{error}</p>}
      <button className="danger-button" disabled={busy || typed !== "DELETE" || !password}>
        {busy ? "Deleting…" : `Permanently delete ${user.email}`}
      </button>
    </form>
  );
}

export default function SettingsDialog({ user, onClose, onSaved, onDeleted }: Props) {
  const sections: { id: Section; label: string }[] = [
    { id: "account", label: "Account" },
    ...(!user.is_admin ? [{ id: "targets" as const, label: "Targets & weight" }] : []),
    { id: "security", label: "Password" },
    ...(!user.is_admin ? [{ id: "delete" as const, label: "Delete account" }] : []),
  ];
  const [section, setSection] = useState<Section>("account");

  return (
    <div className="backdrop" onClick={onClose}>
      <div className="card dialog settings-dialog" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div className="dialog-head">
          <h2 id="settings-title">Settings</h2>
          <button className="ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="settings-body">
          <nav className="settings-nav" role="tablist" aria-label="Settings sections">
            {sections.map((s) => (
              <button key={s.id} role="tab" aria-selected={section === s.id}
                      className={`${section === s.id ? "on" : ""} ${s.id === "delete" ? "danger" : ""}`}
                      onClick={() => setSection(s.id)}>
                {s.label}
              </button>
            ))}
          </nav>
          <div className="settings-panel" role="tabpanel">
            {section === "account" && <AccountSection user={user} />}
            {section === "targets" && <TargetsSection user={user} onSaved={onSaved} />}
            {section === "security" && <SecuritySection />}
            {section === "delete" && <DeleteSection user={user} onDeleted={onDeleted} />}
          </div>
        </div>
      </div>
    </div>
  );
}
