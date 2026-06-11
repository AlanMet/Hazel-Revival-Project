/**
 * Composited mask preview — base photo + dynamic light overlays.
 * Baked-in photo lighting is supplemented (not replaced) via low-opacity
 * screen/soft-light layers clipped to each Chroma zone.
 */

const EFFECTS = ["off", "static", "spectrum", "breathing"];

/** Percentage layout tuned for assets/mask/hero.jpg (Render01 front view). */
const ZONES = {
  externalLeft: { left: "14%", top: "38%", width: "22%", height: "28%" },
  externalRight: { left: "64%", top: "38%", width: "22%", height: "28%" },
  internal: {
    left: "33%",
    top: "22%",
    width: "34%",
    height: "52%",
    clipPath:
      "polygon(8% 0%, 92% 0%, 100% 18%, 98% 88%, 50% 100%, 2% 88%, 0% 18%)",
  },
};

const DEFAULT_STATE = {
  internal: { effect: "static", color: "#44e8ff", color2: "#a855f7", opacity: 0.38 },
  external: { effect: "static", color: "#44ff44", color2: "#ff44aa", opacity: 0.55 },
};

let rafId = 0;
let t0 = performance.now();

function parseColor(hex) {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.replace(/./g, "$&$&") : h, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

function lerpColor(a, b, t) {
  const ca = parseColor(a);
  const cb = parseColor(b);
  const m = (x, y) => Math.round(x + (y - x) * t);
  const hex = (v) => v.toString(16).padStart(2, "0");
  return `#${hex(m(ca.r, cb.r))}${hex(m(ca.g, cb.g))}${hex(m(ca.b, cb.b))}`;
}

function spectrumColor(t) {
  return `hsl(${(t * 360) % 360} 90% 58%)`;
}

function breathingOpacity(base, t) {
  const wave = (Math.sin(t * Math.PI * 2) + 1) / 2;
  return base * (0.35 + wave * 0.65);
}

function resolveZoneStyle(zoneState, now) {
  const elapsed = (now - t0) / 1000;
  const { effect, color, color2, opacity } = zoneState;

  if (effect === "off") {
    return { color: "transparent", opacity: 0 };
  }

  if (effect === "spectrum") {
    return { color: spectrumColor(elapsed * 0.25), opacity };
  }

  if (effect === "breathing") {
    const c = lerpColor(color, color2 ?? color, (Math.sin(elapsed * Math.PI) + 1) / 2);
    return { color: c, opacity: breathingOpacity(opacity, elapsed * 0.6) };
  }

  return { color, opacity };
}

function applyZoneEl(el, zoneState, now, kind) {
  const { color, opacity } = resolveZoneStyle(zoneState, now);
  el.style.setProperty("--zone-color", color);
  el.style.setProperty("--zone-opacity", String(opacity));

  if (kind === "internal") {
    el.dataset.active = zoneState.effect !== "off" ? "1" : "0";
  }
}

function tick(state, els) {
  const now = performance.now();
  applyZoneEl(els.internal, state.internal, now, "internal");
  applyZoneEl(els.externalLeft, state.external, now, "external");
  applyZoneEl(els.externalRight, state.external, now, "external");
  rafId = requestAnimationFrame(() => tick(state, els));
}

function placeZone(el, layout) {
  el.style.left = layout.left;
  el.style.top = layout.top;
  el.style.width = layout.width;
  el.style.height = layout.height;
  if (layout.clipPath) {
    el.style.clipPath = layout.clipPath;
  }
}

/**
 * @param {HTMLElement} root
 * @param {{ internal?: Partial<typeof DEFAULT_STATE.internal>, external?: Partial<typeof DEFAULT_STATE.external> }} [initial]
 */
export function createMaskPreview(root, initial = {}) {
  const state = {
    internal: { ...DEFAULT_STATE.internal, ...initial.internal },
    external: { ...DEFAULT_STATE.external, ...initial.external },
  };

  const els = {
    internal: root.querySelector("[data-zone='internal']"),
    externalLeft: root.querySelector("[data-zone='external-left']"),
    externalRight: root.querySelector("[data-zone='external-right']"),
  };

  placeZone(els.internal, ZONES.internal);
  placeZone(els.externalLeft, ZONES.externalLeft);
  placeZone(els.externalRight, ZONES.externalRight);

  cancelAnimationFrame(rafId);
  t0 = performance.now();
  tick(state, els);

  return {
    getState: () => state,
    setInternal(patch) {
      Object.assign(state.internal, patch);
    },
    setExternal(patch) {
      Object.assign(state.external, patch);
    },
    destroy() {
      cancelAnimationFrame(rafId);
    },
  };
}

export { EFFECTS, DEFAULT_STATE };
