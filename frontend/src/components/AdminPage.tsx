import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { AdminUserDetail, AdminUserRow, AuditRow, ChatMessage } from "../types";
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
