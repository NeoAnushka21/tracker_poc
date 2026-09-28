/**
 * Front-view body figure (male or female) with an arrow from each measurement point.
 * Drawn from a half outline that's mirrored, smoothed with Catmull-Rom curves, so both sides
 * match and the shapes scale cleanly. Wide cards show labelled callouts on both sides; narrow
 * cards (phones) show numbered dots and the page lists the parts below (styles.css "body tab").
 */
import type { KeyboardEvent } from "react";

type Pt = [number, number];
type Sex = "male" | "female";

/** Smooth path through points (Catmull-Rom → cubic Bézier). */
function smooth(pts: Pt[], closed = true): string {
  const n = pts.length;
  const at = (i: number) => (closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]);
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const [p0, p1, p2, p3] = [at(i - 1), at(i), at(i + 1), at(i + 2)];
    const c1: Pt = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2: Pt = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0]},${p2[1]}`;
  }
  return closed ? `${d} Z` : d;
}

const mirror = (pts: Pt[]): Pt[] => pts.map(([x, y]) => [200 - x, y]);

/** Left half (viewer's left) from the neck down the outside, round the foot, up the inner leg. */
const BODY: Record<Sex, Pt[]> = {
  male: [
    [90, 60], [89, 74], [72, 81], [56, 88], [49, 100], [53, 124], [57, 158], [61, 196], [60, 226],
    [57, 252], [58, 300], [63, 350], [61, 382], [67, 420], [62, 438], [90, 441], [88, 420], [90, 382],
    [92, 350], [95, 300], [100, 264],
  ],
  female: [
    [91, 60], [90, 74], [76, 81], [62, 88], [56, 100], [59, 124], [62, 152], [69, 194], [62, 222],
    [53, 250], [56, 300], [64, 350], [63, 382], [68, 420], [63, 438], [90, 441], [88, 420], [90, 382],
    [92, 350], [95, 300], [100, 266],
  ],
};
const ARM: Record<Sex, Pt[]> = {
  male: [
    [52, 90], [42, 104], [38, 138], [35, 172], [31, 206], [29, 238], [25, 262], [33, 274], [41, 263],
    [40, 240], [44, 209], [48, 175], [52, 142], [56, 122],
  ],
  female: [
    [58, 90], [48, 104], [45, 138], [42, 172], [38, 206], [36, 236], [32, 258], [39, 270], [46, 259],
    [45, 238], [49, 208], [53, 175], [56, 142], [60, 122],
  ],
};
const HAIR: Record<Sex, string> = {
  male: "M79,34 C78,14 92,8 100,8 C110,8 123,14 121,34 C117,26 110,22 100,23 C90,22 83,26 79,34 Z",
  female: "M77,40 C74,14 90,7 100,7 C112,7 127,14 123,40 C125,58 127,70 122,82 C118,70 118,52 119,38 "
    + "C113,28 107,24 100,24 C93,24 87,28 81,38 C82,52 82,70 78,82 C73,70 75,58 77,40 Z",
};

/** Where each measurement's arrow points, and which side its label sits on. */
const ANCHORS: Record<Sex, Record<string, { at: Pt; side: "left" | "right" }>> = {
  male: {
    neck_cm: { at: [110, 68], side: "right" }, shoulders_cm: { at: [48, 98], side: "left" },
    chest_cm: { at: [72, 140], side: "left" }, biceps_cm: { at: [41, 140], side: "left" },
    forearm_cm: { at: [36, 204], side: "left" }, wrist_cm: { at: [33, 240], side: "left" },
    waist_cm: { at: [138, 198], side: "right" }, hips_cm: { at: [143, 250], side: "right" },
    thigh_cm: { at: [124, 300], side: "right" }, calf_cm: { at: [134, 382], side: "right" },
  },
  female: {
    neck_cm: { at: [109, 68], side: "right" }, shoulders_cm: { at: [55, 98], side: "left" },
    chest_cm: { at: [74, 138], side: "left" }, biceps_cm: { at: [48, 140], side: "left" },
    forearm_cm: { at: [42, 204], side: "left" }, wrist_cm: { at: [40, 238], side: "left" },
    waist_cm: { at: [131, 194], side: "right" }, hips_cm: { at: [147, 250], side: "right" },
    thigh_cm: { at: [123, 300], side: "right" }, calf_cm: { at: [133, 382], side: "right" },
  },
};

export type FigurePart = { key: string; label: string; value: string | null; change: string | null };

const OFFSET_X = 210;          // the figure sits in the middle of the 620-wide callout view
const LABEL_W = 150;
const LABEL_H = 40;
const GAP = 12;

/** Spread label boxes vertically so they never overlap, keeping each near its point. */
function spread(ys: number[], top = 10, bottom = 460): number[] {
  const out = [...ys];
  for (let i = 1; i < out.length; i++) out[i] = Math.max(out[i], out[i - 1] + LABEL_H + GAP);
  const overflow = out[out.length - 1] + LABEL_H / 2 - bottom;
  if (overflow > 0) for (let i = 0; i < out.length; i++) out[i] -= overflow;
  return out.map((y) => Math.max(y, top + LABEL_H / 2));
}

function Figure({ sex }: { sex: Sex }) {
  const arm = ARM[sex];
  const body = BODY[sex];
  return (
    <g className="bf-figure">
      <path className="bf-skin" d={smooth(arm)} />
      <path className="bf-skin" d={smooth(mirror(arm))} />
      <path className="bf-skin" d={smooth([...body, ...mirror(body.slice(0, -1)).reverse()])} />
      <ellipse className="bf-skin" cx="100" cy="36" rx="20" ry="24" />
      <path className="bf-hair" d={HAIR[sex]} />
    </g>
  );
}

function onKey(e: KeyboardEvent, fn: () => void) {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fn(); }
}

/** Laptop/tablet view: figure in the middle, labelled arrows on both sides. */
export function BodyCallouts({ sex, parts, selected, onSelect }: {
  sex: Sex; parts: FigurePart[]; selected: string | null; onSelect: (key: string) => void;
}) {
  const anchors = ANCHORS[sex];
  const placed = (["left", "right"] as const).flatMap((side) => {
    const list = parts.filter((p) => anchors[p.key]?.side === side)
      .sort((a, b) => anchors[a.key].at[1] - anchors[b.key].at[1]);
    const ys = spread(list.map((p) => anchors[p.key].at[1] + 5));
    return list.map((p, i) => ({ p, side, y: ys[i], at: anchors[p.key].at }));
  });
  return (
    <svg className="bf bf-wide" viewBox="0 0 620 470" role="group" aria-label="Body measurements">
      <defs>
        <marker id="bf-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="bf-arrowhead" />
        </marker>
      </defs>
      <g transform={`translate(${OFFSET_X},5)`}><Figure sex={sex} /></g>
      {placed.map(({ p, side, y, at }) => {
        const ax = at[0] + OFFSET_X;
        const ay = at[1] + 5;
        const boxX = side === "left" ? 20 : 620 - 20 - LABEL_W;
        const edge = side === "left" ? boxX + LABEL_W : boxX;
        const on = selected === p.key;
        return (
          <g key={p.key} className={`bf-callout${on ? " on" : ""}${p.value ? "" : " empty"}`} role="button" tabIndex={0}
             aria-pressed={on} aria-label={`${p.label}: ${p.value ?? "not measured"}. Add a new measurement`}
             onClick={() => onSelect(p.key)} onKeyDown={(e) => onKey(e, () => onSelect(p.key))}>
            <line className="bf-leader" x1={edge} y1={y} x2={ax} y2={ay} markerEnd="url(#bf-arrow)" />
            <circle className="bf-point" cx={ax} cy={ay} r="3.5" />
            <rect className="bf-box" x={boxX} y={y - LABEL_H / 2} width={LABEL_W} height={LABEL_H} rx="10" />
            <text className="bf-label" x={boxX + 12} y={y - 3}>{p.label}</text>
            <text className="bf-value" x={boxX + 12} y={y + 13}>
              {p.value ?? "+ Add"}
              {p.change && <tspan className="bf-change"> {p.change}</tspan>}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Phone view: the figure with numbered dots; the page lists the same numbers below. */
export function BodyDots({ sex, keys, selected, onSelect }: {
  sex: Sex; keys: string[]; selected: string | null; onSelect: (key: string) => void;
}) {
  const anchors = ANCHORS[sex];
  return (
    <svg className="bf bf-narrow" viewBox="0 0 200 450" role="group" aria-label="Body measurement points">
      <Figure sex={sex} />
      {keys.map((k, i) => anchors[k] && (
        <g key={k} className={`bf-dot${selected === k ? " on" : ""}`} role="button" tabIndex={0}
           aria-label={`Point ${i + 1}`} onClick={() => onSelect(k)} onKeyDown={(e) => onKey(e, () => onSelect(k))}>
          <circle cx={anchors[k].at[0]} cy={anchors[k].at[1]} r="9" />
          <text x={anchors[k].at[0]} y={anchors[k].at[1] + 4}>{i + 1}</text>
        </g>
      ))}
    </svg>
  );
}
