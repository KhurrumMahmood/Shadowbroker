/**
 * Design tokens extracted from the ShadowBroker dashboard.
 *
 * These tokens capture the military-HUD aesthetic: near-black backgrounds,
 * cyan accent palette, monospace typography at tiny sizes with wide tracking,
 * semi-transparent panels with backdrop blur, and domain-colored glows.
 *
 * Used by: ArtifactPanel (injects CSS vars into sandboxed iframes),
 * any future reusable components that need consistent theming.
 */

// ─── Backgrounds ───────────────────────────────────────────────────
export const bg = {
  primary: "#000000",
  secondary: "rgb(5, 5, 8)",
  tertiary: "rgb(12, 12, 16)",
  panel: "rgba(0, 0, 0, 0.85)",
  floating: "rgba(0, 0, 0, 0.90)",
  hover: "rgba(8, 51, 68, 0.2)",
} as const;

// ─── Text ──────────────────────────────────────────────────────────
export const text = {
  primary: "rgb(243, 244, 246)",
  secondary: "rgb(34, 211, 238)", // cyan-400
  muted: "rgb(8, 145, 178)", // cyan-600
  heading: "rgb(236, 254, 255)", // cyan-50
} as const;

// ─── Borders ───────────────────────────────────────────────────────
export const border = {
  primary: "rgb(10, 12, 15)",
  secondary: "rgb(20, 24, 28)",
  accent: "rgba(8, 145, 178, 0.4)", // cyan-800/40
  panel: "rgba(8, 145, 178, 0.6)", // cyan-800/60
} as const;

// ─── Cyan Accent Palette ───────────────────────────────────────────
export const cyan = {
  50: "#ecfeff",
  100: "#cffafe",
  200: "#a5f3fc",
  300: "#67e8f9",
  400: "#22d3ee",
  500: "#06b6d4",
  600: "#0891b2",
  700: "#0e7490",
  800: "#155e75",
  900: "#164e63",
  950: "#083344",
} as const;

// ─── Domain Colors (entity type → accent color) ───────────────────
export const domainColors = {
  aviation: { accent: "#22d3ee", border: "#155e75", glow: "rgba(0,255,255,0.15)" },
  private_aviation: { accent: "#fb923c", border: "rgba(249,115,22,0.3)", glow: "rgba(249,115,22,0.15)" },
  private_jets: { accent: "#c084fc", border: "rgba(168,85,247,0.3)", glow: "rgba(168,85,247,0.15)" },
  military: { accent: "#facc15", border: "#854d0e", glow: "rgba(255,200,0,0.15)" },
  tracked: { accent: "#f472b6", border: "rgba(236,72,153,0.3)", glow: "rgba(236,72,153,0.15)" },
  maritime: { accent: "#60a5fa", border: "rgba(59,130,246,0.3)", glow: "rgba(59,130,246,0.15)" },
  seismic: { accent: "#fbbf24", border: "#92400e", glow: "rgba(245,158,11,0.15)" },
  fire: { accent: "#f87171", border: "#991b1b", glow: "rgba(239,68,68,0.2)" },
  infrastructure: { accent: "#a78bfa", border: "#5b21b6", glow: "rgba(167,139,250,0.15)" },
  outages: { accent: "#f87171", border: "#991b1b", glow: "rgba(248,113,113,0.15)" },
  intelligence: { accent: "#4ade80", border: "#166534", glow: "rgba(0,255,128,0.2)" },
  markets: { accent: "#34d399", border: "rgba(52,211,153,0.3)", glow: "rgba(52,211,153,0.15)" },
} as const;

// ─── Typography ────────────────────────────────────────────────────
export const typography = {
  fontFamily: {
    sans: "var(--font-geist-sans), Arial, Helvetica, sans-serif",
    mono: "var(--font-geist-mono), monospace",
  },
  /** All sizes in px — the dashboard uses tiny monospace text */
  fontSize: {
    "2xl": "24px",
    xs: "12px",
    "11": "11px",
    "10": "10px",
    "9": "9px",
    "8": "8px",
    "7": "7px",
  },
  tracking: {
    title: "0.4em",
    subtitle: "0.3em",
    heading: "0.2em",
    label: "0.15em",
    widest: "0.1em",
    wider: "0.05em",
  },
} as const;

// ─── Shadows ───────────────────────────────────────────────────────
export const shadows = {
  panel: "0 4px 30px rgba(0,0,0,0.2)",
  floating: "0 4px 30px rgba(0,0,0,0.5)",
  dropdown: "0 4px 30px rgba(0,0,0,0.4)",
  glow: "0 0 20px rgba(0,255,255,0.1)",
  glowStrong: "0 0 8px rgba(0,255,255,0.2)",
} as const;

// ─── Z-Index Layers ────────────────────────────────────────────────
export const zIndex = {
  content: 10,
  hud: 200,
  sidebar: 201,
  boxSelect: 300,
  floating: 400,
  modal: 9999,
} as const;
