import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { AdminUserDetail, AdminUserRow, AdminWaitlist, AuditRow, ChatMessage, LlmUsageReport, WaitlistRow } from "../types";
import { StatTile } from "./charts";
import { GOALS, MEAL_LABEL, grams, kcal } from "../format";
import { UserAvatar } from "./Avatar";

function when(iso: string | null): string {
  if (!iso) return "–";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function UserDetail({ user, onClose }: { user: AdminUserRow; onClose: () => void }) {
  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [chat, setChat] = useState<ChatMessage[] | null>(null);
  const [tab, setTab] = useState<"logs" | "foods" | "chat">("logs");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null);
    setChat(null);
    setTab("logs");
    api.adminUser(user.id, 30).then(setDetail).catch((e) => setError(e.message));
  }, [user.id]);

  useEffect(() => {
    if (tab === "chat" && chat === null) api.adminChat(user.id).then(setChat).catch((e) => setError(e.message));
  }, [tab, chat, user.id]);

  const p = detail?.profile;
  return (
    <div className="admin-detail card">
      <div className="dialog-head">
        <h3 className="admin-detail-title">
          <UserAvatar name={user.preferred_name} email={user.email} size={32} /> {user.email}
        </h3>
        <button className="ghost" onClick={onClose} aria-label="Close">✕</button>
      </div>
      {error && <p className="error">{error}</p>}
      {!detail && !error && <p className="muted">Loading…</p>}
      {p && (
        <>
          <dl className="admin-facts">
            <div><dt>Name</dt><dd>{p.preferred_name ?? "–"}</dd></div>
            <div><dt>Goal</dt><dd>{p.goal_type ? GOALS[p.goal_type] ?? p.goal_type : "–"}</dd></div>
            <div><dt>Sex / DOB</dt><dd>{p.sex ?? "–"} / {p.date_of_birth ?? "–"}</dd></div>
            <div><dt>Height / weight</dt><dd>{p.height_cm ?? "–"} cm / {p.weight_kg ?? "–"} kg</dd></div>
            <div><dt>Targets</dt><dd>{p.targets ? `${p.targets.calories} kcal · P ${p.targets.protein_g} · C ${p.targets.carbs_g} · F ${p.targets.fat_g}` : "–"}</dd></div>
            <div><dt>Time zone</dt><dd>{p.timezone}</dd></div>
            <div><dt>Joined</dt><dd>{when(p.created_at)}</dd></div>
            <div><dt>Consent</dt><dd>{when(p.consented_at)}</dd></div>
          </dl>

          <div className="segmented admin-tabs" role="tablist">
            {(["logs", "foods", "chat"] as const).map((t) => (
              <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
                {t === "logs" ? `Logs (30 days)` : t === "foods" ? `Foods (${detail.foods.length})` : "Chat"}
              </button>
            ))}
          </div>

          {tab === "logs" && (
            detail.days.length === 0 ? <p className="muted">No logs in the last 30 days.</p> : (
              <div className="admin-days">
                {[...detail.days].reverse().map((d) => (
                  <div key={d.date} className="admin-day">
                    <div className="meal-head"><span>{d.date}</span><span className="num">{kcal(d.totals.calories)}</span></div>
                    <div className="meal-macros">P {grams(d.totals.protein_g)} · Fiber {grams(d.totals.fiber_g)} · C {grams(d.totals.carbs_g)} · F {grams(d.totals.fat_g)}</div>
                    <ul className="meal-items">
                      {d.entries.flatMap((e) => e.items.map((it, i) => (
                        <li key={`${e.id}-${i}`}>
                          <span className="meal-item-name"><span className="muted">{MEAL_LABEL[e.meal_type] ?? e.meal_type} · </span>{it.ingredient_name}</span>
                          <span className="muted meal-item-qty">{it.quantity} {it.unit}</span>
                          <span className="num">{Math.round(it.calories)}</span>
                        </li>
                      )))}
                    </ul>
                  </div>
                ))}
              </div>
            )
          )}

          {tab === "foods" && (
            detail.foods.length === 0 ? <p className="muted">No saved foods.</p> : (
              <ul className="food-list">
                {detail.foods.map((f) => (
                  <li key={f.id} className="admin-food">
                    <b>{f.name}</b>{f.kind === "recipe" && <span className="source-tag recipe">recipe</span>}
                    <span className="muted small"> {f.measures}: {Math.round(f.calories)} kcal · P {grams(f.protein_g)} · C {grams(f.carbs_g)} · F {grams(f.fat_g)}</span>
                  </li>
                ))}
              </ul>
            )
          )}

          {tab === "chat" && (
            chat === null ? <p className="muted">Loading…</p> : chat.length === 0 ? <p className="muted">No messages.</p> : (
              <div className="admin-chat">
                {chat.filter((m) => m.role !== "event").map((m) => (
                  <div key={m.id} className={`admin-msg ${m.role}`}>
                    <span className="muted small">{m.role === "user" ? "User" : "MacBro"} · {when(m.created_at)}</span>
                    <div>{m.content}</div>
                  </div>
                ))}
              </div>
            )
          )}
        </>
      )}
    </div>
  );
}

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUserRow[] | null>(null);
  const [audit, setAudit] = useState<AuditRow[] | null>(null);
  const [selected, setSelected] = useState<AdminUserRow | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminUsers().then(setUsers).catch((e) => setError(e.message));
  }, []);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (users ?? []).filter((u) => !q || u.email.toLowerCase().includes(q) || (u.preferred_name ?? "").toLowerCase().includes(q));
  }, [users, query]);

  return (
    <section className="admin">
      <div className="card">
        <div className="analysis-head">
          <div>
            <h2>Admin</h2>
            <p className="muted small">Read-only. Every time you open a user's data it's recorded in the audit log.</p>
          </div>
          <input type="search" placeholder="Search users" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search users" />
        </div>
        {error && <p className="error">{error}</p>}
        {!users && !error && <p className="muted">Loading…</p>}
        {users && (
          <div className="table-scroll">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th><th>Last login</th><th>Logins</th><th>Joined</th>
                  <th>Entries</th><th>Foods</th><th>Water</th><th>Messages</th><th>Last logged</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((u) => (
                  <tr key={u.id} className={selected?.id === u.id ? "on" : ""} onClick={() => setSelected(u)}
                      tabIndex={0} onKeyDown={(e) => e.key === "Enter" && setSelected(u)}>
                    <td>
                      <span className="admin-user">
                        <UserAvatar name={u.preferred_name} email={u.email} size={26} />
                        <span><b>{u.preferred_name ?? "–"}</b><br /><span className="muted small">{u.email}</span></span>
                      </span>
                      {!u.onboarded && <span className="source-tag">not onboarded</span>}
                    </td>
                    <td>{when(u.last_login_at)}</td>
                    <td className="num">{u.login_count}</td>
                    <td>{when(u.created_at)}</td>
                    <td className="num">{u.entries}</td>
                    <td className="num">{u.foods}</td>
                    <td className="num">{u.water_logs}</td>
                    <td className="num">{u.chat_messages}</td>
                    <td>{when(u.last_logged_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && <UserDetail user={selected} onClose={() => setSelected(null)} />}

      <WaitlistPanel />
      <LlmUsagePanel />
      <TwoStepPanel />

      <details className="card audit" onToggle={(e) => (e.target as HTMLDetailsElement).open && audit === null && api.adminAudit().then(setAudit).catch(() => setAudit([]))}>
        <summary>Audit log</summary>
        {audit === null ? <p className="muted">Loading…</p> : (
          <ul className="audit-list">
            {audit.map((a, i) => (
              <li key={i}><span className="muted">{when(a.at)}</span> {a.admin} · {a.action}{a.user ? ` · ${a.user}` : ""}</li>
            ))}
          </ul>
        )}
      </details>
    </section>
  );
}

const n = (v: number) => v.toLocaleString();

/** People who joined the waitlist on the welcome page. Approve lets their email create an
 *  account and emails them the invitation; Remove takes them off the list. */
function WaitlistPanel() {
  const [data, setData] = useState<AdminWaitlist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);   // id of the row being changed
  const [note, setNote] = useState<string | null>(null);

  const fetchList = () => api.adminWaitlist().then(setData).catch((e) => setError(e.message));
  useEffect(() => { fetchList(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  function load() {
    setError(null);
    setNote(null);
    fetchList();
  }

  async function change(row: WaitlistRow, action: "approve" | "remove") {
    if (action === "remove" && !window.confirm(`Take ${row.email} off the waitlist?`)) return;
    setBusy(row.id);
    setError(null);
    setNote(null);
    try {
      if (action === "approve") {
        const updated = await api.adminWaitlistApprove(row.id);
        setData((d) => d && { ...d, entries: d.entries.map((e) => (e.id === row.id ? updated : e)) });
        setNote(data?.email_enabled ? `Invitation emailed to ${row.email}.`
          : `${row.email} can now sign up. Email isn't set up, so tell them yourself.`);
      } else {
        await api.adminWaitlistRemove(row.id);
        setData((d) => d && { ...d, entries: d.entries.filter((e) => e.id !== row.id) });
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const waiting = data?.entries.filter((e) => !e.approved_at).length ?? 0;
  return (
    <section className="card waitlist" aria-labelledby="waitlist-title">
      <div className="analysis-head">
        <div>
          <h2 id="waitlist-title">Waitlist</h2>
          <p className="muted small">
            {data?.join_mode === "waitlist"
              ? "Sign-up is by invitation (JOIN_MODE=waitlist): only approved emails can create an account."
              : "Sign-up is open to everyone (JOIN_MODE=open), so the welcome page doesn't show the form right now."}
          </p>
        </div>
        <button type="button" className="ghost" onClick={load}>Refresh</button>
      </div>
      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}
      {note && <p className="ok small" role="status">{note}</p>}
      {data && (data.entries.length === 0 ? <p className="muted">Nobody on the list yet.</p> : (
        <>
          <p className="small"><b>{waiting}</b> waiting · <b>{data.entries.length - waiting}</b> approved</p>
          <div className="table-scroll">
            <table className="admin-table">
              <thead><tr><th>Person</th><th>Wants to track</th><th>Joined</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.id}>
                    <td><b>{e.name}</b><br /><span className="muted small">{e.email}</span></td>
                    <td className="small">{e.interest ?? <span className="muted">–</span>}</td>
                    <td>{when(e.created_at)}</td>
                    <td>{e.has_account ? <span className="ok">● has an account</span>
                      : e.approved_at ? <span className="ok">● approved {when(e.approved_at)}</span>
                      : <span className="warn">● waiting</span>}</td>
                    <td>
                      <div className="row tight">
                        {!e.has_account && (
                          <button type="button" className={e.approved_at ? "ghost" : "primary"} disabled={busy === e.id}
                                  onClick={() => change(e, "approve")}>{e.approved_at ? "Resend invite" : "Approve"}</button>
                        )}
                        <button type="button" className="ghost" disabled={busy === e.id}
                                onClick={() => change(e, "remove")} aria-label={`Remove ${e.email}`}>Remove</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ))}
    </section>
  );
}

/** Model calls, tokens and the state of each model in the pool (open-source models only). */
function LlmUsagePanel() {
  const [hours, setHours] = useState(24);
  const [data, setData] = useState<LlmUsageReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load(h = hours) {
    setError(null);
    api.adminLlmUsage(h).then(setData).catch((e) => setError(e.message));
  }
  useEffect(() => { load(hours); }, [hours]); // eslint-disable-line react-hooks/exhaustive-deps

  const t = data?.totals;
  return (
    <section className="card llm-usage" aria-labelledby="llm-usage-title">
      <div className="analysis-head">
        <div>
          <h2 id="llm-usage-title">AI usage</h2>
          <p className="muted small">Open-source models only. Fast-path replies are answered by rules, with no model call.</p>
        </div>
        <div className="row tight">
          <div className="segmented" role="radiogroup" aria-label="Period">
            {[24, 24 * 7].map((h) => (
              <button key={h} type="button" className={hours === h ? "on" : ""} aria-pressed={hours === h}
                      onClick={() => setHours(h)}>{h === 24 ? "24 h" : "7 days"}</button>
            ))}
          </div>
          <button type="button" className="ghost" onClick={() => load()}>Refresh</button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}
      {data && t && (
        <>
          <div className="stat-row usage-stats">
            <StatTile label="User messages" value={n(t.user_messages)} />
            <StatTile label="Model calls" value={n(t.model_calls)} sub={`${n(t.tokens)} tokens`} />
            <StatTile label="Answered by rules" value={t.fastpath_share_pct == null ? "–" : `${t.fastpath_share_pct}%`}
                      sub={`${n(t.fastpath_replies)} fast-path replies`} />
            <StatTile label="Problems" value={n(t.errors + t.rate_limited)}
                      sub={`${n(t.rate_limited)} rate-limited · ${n(t.escalations)} escalated`} />
          </div>

          <h3>Models in the pool</h3>
          <div className="table-scroll">
            <table className="admin-table">
              <thead><tr><th>Model</th><th>Tier</th><th>Licence</th><th>Status</th><th>Last error</th></tr></thead>
              <tbody>
                {data.pool.map((p, i) => p.error ? (
                  <tr key={i}><td colSpan={5} className="error">{p.error}</td></tr>
                ) : (
                  <tr key={i}>
                    <td><b>{p.model}</b><br /><span className="muted small">{p.provider}</span></td>
                    <td>{p.tier}</td>
                    <td>{p.license ?? "–"}</td>
                    <td>{p.available ? <span className="ok">● available</span>
                      : <span className="warn">● cooling down {Math.ceil((p.cooldown_seconds ?? 0) / 60)} min</span>}</td>
                    <td className="muted small usage-error">{p.last_error ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>Calls by model</h3>
          {data.by_model.length === 0 ? <p className="muted small">No model calls in this period.</p> : (
            <div className="table-scroll">
              <table className="admin-table">
                <thead><tr><th>Model</th><th>Tier</th><th>Calls</th><th>OK</th><th>Rate-limited</th><th>Errors</th>
                  <th>Tokens in</th><th>Tokens out</th><th>Avg time</th></tr></thead>
                <tbody>
                  {data.by_model.map((m) => (
                    <tr key={`${m.provider}-${m.model}-${m.tier}`}>
                      <td><b>{m.model}</b><br /><span className="muted small">{m.provider}</span></td>
                      <td>{m.tier}</td>
                      <td className="num">{n(m.calls)}</td><td className="num">{n(m.ok)}</td>
                      <td className="num">{n(m.rate_limited)}</td><td className="num">{n(m.errors)}</td>
                      <td className="num">{n(m.prompt_tokens)}</td><td className="num">{n(m.completion_tokens)}</td>
                      <td className="num">{m.avg_latency_ms == null ? "–" : `${(m.avg_latency_ms / 1000).toFixed(1)} s`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="chart-grid-2">
            <div>
              <h3>Calls by message type</h3>
              {data.by_intent.length === 0 ? <p className="muted small">–</p> : (
                <ul className="usage-list">
                  {data.by_intent.map((i) => <li key={i.intent}><span>{i.intent}</span><span className="num">{n(i.calls)} calls · {n(i.tokens)} tokens</span></li>)}
                </ul>
              )}
            </div>
            <div>
              <h3>Answered by rules</h3>
              {Object.keys(data.fastpath).length === 0 ? <p className="muted small">–</p> : (
                <ul className="usage-list">
                  {Object.entries(data.fastpath).map(([k, v]) => <li key={k}><span>{k.replace("_", " ")}</span><span className="num">{n(v)}</span></li>)}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}


/** Two-step sign-in for this admin account: scan a QR code, confirm one code, then logins need a code. */
function TwoStepPanel() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [setup, setSetup] = useState<{ secret: string; qr_svg_data_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.adminTotp().then((t) => setEnabled(t.enabled)).catch((e) => setError(e.message)); }, []);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try { await fn(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <section className="card two-step" aria-labelledby="two-step-title">
      <h2 id="two-step-title">Two-step sign-in</h2>
      <p className="muted small">
        Admin login also asks for a 6-digit code from an authenticator app (Google Authenticator, Microsoft
        Authenticator, Authy…). Admin sessions last 12 hours.
      </p>
      {enabled === null && !error && <p className="muted">Loading…</p>}
      {enabled === true && (
        <form className="settings-form" onSubmit={(e) => { e.preventDefault(); run(async () => {
          await api.adminTotpDisable(password, code); setEnabled(false); setCode(""); setPassword(""); }); }}>
          <p className="ok">On. Logins need your password and a code.</p>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
          <label>Current code<input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" required /></label>
          <button disabled={busy}>Turn off</button>
        </form>
      )}
      {enabled === false && !setup && (
        <button className="primary" disabled={busy} onClick={() => run(async () => { setSetup(await api.adminTotpSetup()); })}>
          Set up two-step sign-in
        </button>
      )}
      {enabled === false && setup && (
        <form className="settings-form" onSubmit={(e) => { e.preventDefault(); run(async () => {
          await api.adminTotpEnable(code); setEnabled(true); setSetup(null); setCode(""); }); }}>
          <p>1. In your authenticator app, add an account and scan this code:</p>
          <img className="totp-qr" src={setup.qr_svg_data_uri} alt="QR code for your authenticator app" width={200} height={200} />
          <p className="muted small">Can't scan? Enter this key instead: <code className="totp-key">{setup.secret}</code></p>
          <label>2. Type the 6-digit code it shows
            <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" required />
          </label>
          <button className="primary" disabled={busy}>Turn on</button>
        </form>
      )}
      {error && <p className="error small">{error}</p>}
    </section>
  );
}
