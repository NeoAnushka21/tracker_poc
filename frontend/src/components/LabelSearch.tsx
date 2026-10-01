import { useEffect, useState } from "react";
import { api } from "../api";
import type { Label } from "../types";
import { grams } from "../format";
import PackScanner, { type PackReading } from "./PackScanner";

/** Search Open Food Facts for a pack label (product and brand, or a barcode) and pick one; the
 *  words can also come from the pack itself (Scan or photo: barcode, or the name read off the front).
 *  Used by Check label on a saved food, + Add → Branded product, and the chat's pack finder. */
export default function LabelSearch({ initialQuery, busyCode, onPick, scanFirst = false, pickText = "Use this" }: {
  initialQuery: string;
  /** The barcode being saved, if any: its button shows "Saving…" and the others wait. */
  busyCode?: string | null;
  onPick: (label: Label) => void;
  /** Open the scanner straight away (the chat's scan button). */
  scanFirst?: boolean;
  pickText?: string;
}) {
  const [q, setQ] = useState(initialQuery);
  const [results, setResults] = useState<Label[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(scanFirst);
  const [readFrom, setReadFrom] = useState<PackReading["kind"] | null>(null);

  function scanned(r: PackReading) {
    setScanning(false);
    setReadFrom(r.kind);
    setQ(r.text);
    void search(r.text);
  }

  async function search(text: string) {
    if (text.trim().length < 2) return;
    setSearching(true);
    setError(null);
    try {
      setResults(await api.labelSearch(text.trim()));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSearching(false);
    }
  }

  // Search straight away when opened with words already filled in.
  useEffect(() => { if (initialQuery.trim().length >= 2) search(initialQuery); }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  const busy = searching || !!busyCode;
  return (
    <div className="label-finder">
      <div className="label-search">
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Product and brand, or barcode"
               placeholder="Product and brand, or the barcode number"
               onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); search(q); } }} />
        <button type="button" className="primary" disabled={busy} onClick={() => search(q)}>
          {searching ? "Searching…" : "Search"}
        </button>
        <button type="button" className="scan-btn" disabled={busy} onClick={() => setScanning(true)}
                title="Scan the barcode or take a photo of the pack">
          <span aria-hidden="true">▥</span> Scan or photo
        </button>
      </div>
      {readFrom && (
        <p className="muted small scan-note">
          {readFrom === "barcode" ? "Barcode read from the pack." : "Words read from your photo: fix them above if they're off, then Search."}
        </p>
      )}
      {scanning && <PackScanner onRead={scanned} onClose={() => setScanning(false)} />}
      {error && <p className="error small">{error}</p>}
      {results?.length === 0 && (
        <p className="muted small">No complete label found. Try other words or the barcode number, or type the values from the pack.</p>
      )}
      {results && results.length > 0 && (
        <ul className="label-results">
          {results.map((l) => (
            <li key={l.code}>
              <div className="label-product">
                <b>{l.name}</b>{l.brand && <span className="muted"> · {l.brand}</span>}
                {l.in_india && <span className="source-tag">sold in India</span>}
                <div className="muted small">
                  {[l.pack && `pack ${l.pack}`, l.serving_size && `serving ${l.serving_size}`, `barcode ${l.code}`].filter(Boolean).join(" · ")}
                </div>
                <div className="small num">
                  <b>{Math.round(l.calories)} kcal</b> per {l.ref_qty} {l.ref_unit} · P {grams(l.protein_g)} · C {grams(l.carbs_g)} · F {grams(l.fat_g)}
                  {l.fiber_g ? ` · Fiber ${grams(l.fiber_g)}` : ""}
                </div>
              </div>
              <button type="button" className="ghost" onClick={() => onPick(l)} disabled={busy}>
                {busyCode === l.code ? "Saving…" : pickText}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">
        Labels from <a href="https://world.openfoodfacts.org" target="_blank" rel="noreferrer">Open Food Facts</a>, an
        open database filled in by volunteers (ODbL). Compare with your pack before you use one.
      </p>
    </div>
  );
}
