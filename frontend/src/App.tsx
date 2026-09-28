import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { User } from "./types";
import AuthScreen from "./components/AuthScreen";
import Onboarding from "./components/Onboarding";
import Chat from "./components/Chat";
import Dashboard from "./components/Dashboard";
import SettingsDialog from "./components/SettingsDialog";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Bumped whenever confirmed data changes, so the dashboard refetches.
  const [dataVersion, setDataVersion] = useState(0);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) setError(e.message);
      })
      .finally(() => setLoading(false));
  }, []);

  async function logout() {
    await api.logout();
    setUser(null);
  }

  if (loading) return <div className="center muted">Loading…</div>;
  if (error) return <div className="center error">Couldn't reach the server: {error}</div>;
  if (!user) return <AuthScreen onAuthed={setUser} />;
  if (!user.onboarded) return <Onboarding onDone={setUser} />;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">Macro Tracker</span>
        <div className="topbar-actions">
          <button className="ghost" onClick={() => setShowSettings(true)}>Targets &amp; weight</button>
          <button className="ghost" onClick={logout}>Log out</button>
        </div>
      </header>
      <main className="layout">
        <Chat user={user} onDataChanged={() => setDataVersion((v) => v + 1)} />
        <Dashboard dataVersion={dataVersion} />
      </main>
      {showSettings && (
        <SettingsDialog
          user={user}
          onClose={() => setShowSettings(false)}
          onSaved={(u) => {
            setUser(u);
            setDataVersion((v) => v + 1);
          }}
        />
      )}
    </div>
  );
}
