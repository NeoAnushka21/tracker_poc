/**
 * Small hand-rolled SVG charts. Colours are CSS variables applied via `style`, so both
 * themes work without re-rendering. Conventions (from the data-viz guidance): one y-axis,
 * recessive grid and no axis lines, rounded bar tops, hover + keyboard tooltips with hit areas wider than
 * the marks, a legend for 2+ series, and a data table for every chart.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

// ---------- helpers ----------

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(600);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(240, Math.floor(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

/** A round axis maximum: 1, 2, 2.5, 5 x 10^k above the data. */
export function niceMax(v: number): number {
  if (v <= 0) return 1;
  const exp = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) if (v <= m * exp) return m * exp;
  return 10 * exp;
}

function fmt(v: number): string {
  return Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : `${Math.round(v)}`;
}

/** Bar path with rounded top corners, anchored flat to the baseline. */
function barPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(7, w / 2, h);
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
}

const M = { top: 24, right: 10, bottom: 26, left: 40 };

function Tooltip({ x, width, children }: { x: number; width: number; children: ReactNode }) {
  const left = Math.min(Math.max(x, 70), width - 70);
  return <div className="chart-tooltip" style={{ left }} role="status">{children}</div>;
}

function YGrid({ max, innerW, innerH, unit }: { max: number; innerW: number; innerH: number; unit: string }) {
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  return (
    <g>
      {ticks.map((t) => {
        const y = innerH - (t / max) * innerH;
        return (
          <g key={t}>
            {t > 0 && <line x1={0} x2={innerW} y1={y} y2={y} className="chart-grid" />}
            <text x={-6} y={y} dy="0.32em" textAnchor="end" className="chart-tick">{fmt(t)}</text>
          </g>
        );
      })}
      <text x={-M.left + 2} y={-14} className="chart-tick">{unit}</text>
    </g>
  );
}

function xLabelEvery(n: number, innerW: number): number {
  return Math.max(1, Math.ceil(n / Math.max(1, Math.floor(innerW / 44))));
}

export type Point = { label: string; title: string; value: number | null; target?: number | null };

// ---------- bar chart (one series + optional per-day target) ----------

export function BarChart({ points, color, unit, height = 200, valueLabel, ariaLabel }: {
  points: Point[]; color: string; unit: string; height?: number; valueLabel: string; ariaLabel: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const innerW = width - M.left - M.right;
  const innerH = height - M.top - M.bottom;
  const max = niceMax(Math.max(1, ...points.map((p) => Math.max(p.value ?? 0, p.target ?? 0))) * 1.08);
  const band = innerW / points.length;
  const barW = Math.max(3, Math.min(28, band * 0.62));
  const every = xLabelEvery(points.length, innerW);
  const hasTarget = points.some((p) => p.target);
  const hp = hover != null ? points[hover] : null;

  return (
    <div className="chart" ref={ref}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        <g transform={`translate(${M.left},${M.top})`}>
          <YGrid max={max} innerW={innerW} innerH={innerH} unit={unit} />
          {points.map((p, i) => {
            const cx = i * band + band / 2;
            const h = p.value ? (p.value / max) * innerH : 0;
            const ty = p.target ? innerH - (p.target / max) * innerH : null;
            return (
              <g key={i} className={hover === i ? "chart-hover" : ""}>
                {h > 0 && <path d={barPath(cx - barW / 2, innerH - h, barW, h)} style={{ fill: color }} className="chart-bar" />}
                {ty != null && <line x1={cx - band / 2 + 2} x2={cx + band / 2 - 2} y1={ty} y2={ty} className="chart-target" />}
                {i % every === 0 && <text x={cx} y={innerH + 16} textAnchor="middle" className="chart-tick">{p.label}</text>}
                <rect
                  x={i * band} y={0} width={band} height={innerH} className="chart-hit"
                  tabIndex={0} aria-label={`${p.title}: ${p.value == null ? "not logged" : `${Math.round(p.value)} ${unit}`}`}
                  onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(i)} onBlur={() => setHover(null)}
                />
              </g>
            );
          })}
        </g>
      </svg>
      {hp && (
        <Tooltip x={M.left + (hover! + 0.5) * band} width={width}>
          <b>{hp.title}</b>
          <div><i className="tt-swatch" style={{ background: color }} />{valueLabel}: {hp.value == null ? "not logged" : `${Math.round(hp.value)} ${unit}`}</div>
          {hp.target ? <div className="muted">Target: {Math.round(hp.target)} {unit}</div> : null}
        </Tooltip>
      )}
      {hasTarget && <div className="chart-legend"><span><i className="legend-dash" />Daily target</span></div>}
    </div>
  );
}

// ---------- multi-line chart ----------

export type Series = { key: string; label: string; color: string; values: (number | null)[] };

export function LineChart({ labels, titles, series, unit, height = 220, ariaLabel }: {
  labels: string[]; titles: string[]; series: Series[]; unit: string; height?: number; ariaLabel: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const innerW = width - M.left - M.right;
  const innerH = height - M.top - M.bottom;
  const n = labels.length;
  const max = niceMax(Math.max(1, ...series.flatMap((s) => s.values.map((v) => v ?? 0))) * 1.08);
  const x = (i: number) => (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const y = (v: number) => innerH - (v / max) * innerH;
  const every = xLabelEvery(n, innerW);
  const band = n > 1 ? innerW / (n - 1) : innerW;

  function path(values: (number | null)[]): string {
    let d = "";
    let pen = false;
    values.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      d += `${pen ? "L" : "M"}${x(i)},${y(v)} `;
      pen = true;
    });
    return d;
  }

  return (
    <div className="chart" ref={ref}>
      <div className="chart-legend top">
        {series.map((s) => <span key={s.key}><i className="legend-swatch" style={{ background: s.color }} />{s.label}</span>)}
      </div>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        <g transform={`translate(${M.left},${M.top})`}>
          <YGrid max={max} innerW={innerW} innerH={innerH} unit={unit} />
          {labels.map((l, i) => i % every === 0 && (
            <text key={i} x={x(i)} y={innerH + 16} textAnchor="middle" className="chart-tick">{l}</text>
          ))}
          {hover != null && <line x1={x(hover)} x2={x(hover)} y1={0} y2={innerH} className="chart-crosshair" />}
          {series.map((s) => (
            <g key={s.key}>
              <path d={path(s.values)} className="chart-line" style={{ stroke: s.color }} />
              {s.values.map((v, i) => v != null && (
                <circle key={i} cx={x(i)} cy={y(v)} r={hover === i ? 5 : 4} className="chart-dot" style={{ fill: s.color }} />
              ))}
            </g>
          ))}
          {labels.map((_, i) => (
            <rect
              key={i} x={x(i) - band / 2} y={0} width={band} height={innerH} className="chart-hit"
              tabIndex={0} aria-label={`${titles[i]}: ${series.map((s) => `${s.label} ${s.values[i] == null ? "not logged" : Math.round(s.values[i]!)}`).join(", ")}`}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)} onBlur={() => setHover(null)}
            />
          ))}
        </g>
      </svg>
      {hover != null && (
        <Tooltip x={M.left + x(hover)} width={width}>
          <b>{titles[hover]}</b>
          {series.map((s) => (
            <div key={s.key}>
              <i className="tt-swatch" style={{ background: s.color }} />{s.label}:{" "}
              {s.values[hover] == null ? "not logged" : `${Math.round(s.values[hover]!)} ${unit}`}
            </div>
          ))}
        </Tooltip>
      )}
    </div>
  );
}

// ---------- 100% stacked bar (part-to-whole, few segments) ----------

export type Segment = { key: string; label: string; value: number; color: string; detail?: string };

export function StackedBar({ segments, ariaLabel }: { segments: Segment[]; ariaLabel: string }) {
  const [hover, setHover] = useState<string | null>(null);
  const total = segments.reduce((s, x) => s + x.value, 0);
  if (total <= 0) return <p className="muted small">Nothing logged yet.</p>;
  return (
    <div className="stacked" role="group" aria-label={ariaLabel}>
      <div className="stacked-bar">
        {segments.filter((s) => s.value > 0).map((s) => (
          // Hover and focus only show the tooltip; the value is also in each segment's label.
          // oxlint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
          <div
            key={s.key}
            className={`stacked-seg ${hover && hover !== s.key ? "dim" : ""}`}
            style={{ flexGrow: s.value, background: s.color }}
            role="img"
            // Focusable on purpose: focus shows the same tooltip as hover, for keyboard users.
            // oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex
            tabIndex={0}
            onMouseEnter={() => setHover(s.key)} onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(s.key)} onBlur={() => setHover(null)}
            aria-label={`${s.label}: ${Math.round((s.value / total) * 100)}%`}
          />
        ))}
      </div>
      <div className="stacked-labels">
        {segments.map((s) => (
          <span key={s.key} className={hover === s.key ? "on" : ""}>
            <i className="legend-swatch" style={{ background: s.color }} />
            {s.label} <b>{Math.round((s.value / total) * 100)}%</b>
            {s.detail && <span className="muted"> · {s.detail}</span>}
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------- data table fallback ----------

export function DataTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  return (
    <details className="chart-table">
      <summary>Show data table</summary>
      <div className="table-scroll">
        <table>
          <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </details>
  );
}

export type StatIconName = "flame" | "bolt" | "target" | "drop";

const STAT_ICONS: Record<StatIconName, ReactNode> = {
  flame: <path d="M12 2c1 3.5 5 5.5 5 11a5 5 0 0 1-10 0c0-2.4 1-4 2.5-5.5C9.8 9.8 11 11 12 11c-.5-3 0-6 0-9z" />,
  bolt: <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />,
  target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" /></>,
  drop: <path d="M12 3c3.5 4.4 6 7.9 6 11a6 6 0 0 1-12 0c0-3.1 2.5-6.6 6-11z" />,
};

export function StatTile({ label, value, sub, icon }: { label: string; value: string; sub?: ReactNode; icon?: StatIconName }) {
  return (
    <div className={`stat-tile ${icon ?? ""}`}>
      {icon && (
        <svg className="stat-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
             strokeWidth="1.6" strokeLinejoin="round">{STAT_ICONS[icon]}</svg>
      )}
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
