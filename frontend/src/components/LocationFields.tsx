import { useEffect, useState } from "react";
import { AppLogo } from "./Avatar";
import { api, type Country } from "../api";
import type { User } from "../types";

let cached: Promise<Country[]> | null = null;
/** The country list (~70 KB), fetched once per page load and shared by every form. */
function loadCountries(): Promise<Country[]> {
  cached ??= api.countries().catch((e) => { cached = null; throw e; });
  return cached;
}

/** Country (required) and region (optional) dropdowns. Only values from the list can be picked. */
export function LocationFields({ country, region, onChange }: {
  country: string; region: string; onChange: (country: string, region: string) => void;
}) {
  const [countries, setCountries] = useState<Country[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { loadCountries().then(setCountries).catch((e) => setError(e.message)); }, []);
  // Only one country offered (India for now): pick it, so only the optional region is left.
  useEffect(() => {
    if (countries?.length === 1 && !country) onChange(countries[0].code, "");
  }, [countries, country, onChange]);
  const regions = countries?.find((c) => c.code === country)?.regions ?? [];

  return (
    <div className="row">
      <label>
        Country
        <select value={country} required disabled={!countries}
                onChange={(e) => onChange(e.target.value, "")}>
          <option value="" disabled>{countries ? "Select your country" : "Loading…"}</option>
          {countries?.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select>
        {countries?.length === 1 && <span className="muted small">Available in {countries[0].name} for now.</span>}
        {error && <span className="error small">{error}</span>}
      </label>
      <label>
        State / region <span className="muted">(optional)</span>
        <select value={region} disabled={!country || regions.length === 0}
                onChange={(e) => onChange(country, e.target.value)}>
          <option value="">{country ? "Not specified" : "Pick a country first"}</option>
          {regions.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </label>
    </div>
  );
}

/** Once, for accounts created before country and region were asked. */
export function LocationGate({ user, onSaved, onLogout }: {
  user: User; onSaved: (u: User) => void; onLogout: () => void;
}) {
  const [country, setCountry] = useState(user.country ?? "");
  const [region, setRegion] = useState(user.region ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSaved(await api.setLocation(country, region || null));
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <form className="card auth-card" onSubmit={save}>
        <div className="auth-brand">
          <AppLogo size={56} />
          <div>
            <h1>Where do you live?</h1>
            <p className="muted">We've added this to your profile. It takes a few seconds.</p>
          </div>
        </div>
        <LocationFields country={country} region={region} onChange={(c, r) => { setCountry(c); setRegion(r); }} />
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={!country || busy}>{busy ? "Saving…" : "Save and continue"}</button>
        <button type="button" className="link" onClick={onLogout}>Log out instead</button>
      </form>
    </div>
  );
}
