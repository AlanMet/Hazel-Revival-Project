import { BluetoothTransport } from "./bluetooth.js";
import { ZephyrOrchestrator } from "./orchestrator.js";
import { bindUi } from "./ui.js";
import { createMaskPreview } from "./mask-preview.js";

const orchestrator = new ZephyrOrchestrator(new BluetoothTransport());

bindUi(orchestrator, {
  statusEl: document.getElementById("status"),
  connectBtn: document.getElementById("connect"),
  disconnectBtn: document.getElementById("disconnect"),
});

const maskPreview = createMaskPreview(document.getElementById("mask-preview"));

function bindLightingPanel(zone, prefix) {
  const effectEl = document.getElementById(`${prefix}-effect`);
  const colorEl = document.getElementById(`${prefix}-color`);
  const color2El = document.getElementById(`${prefix}-color2`);
  const opacityEl = document.getElementById(`${prefix}-opacity`);

  const apply = () => {
    const patch = {
      effect: effectEl.value,
      color: colorEl.value,
      color2: color2El.value,
      opacity: Number(opacityEl.value),
    };
    zone === "internal" ? maskPreview.setInternal(patch) : maskPreview.setExternal(patch);
  };

  for (const el of [effectEl, colorEl, color2El, opacityEl]) {
    el.addEventListener("input", apply);
  }
}

bindLightingPanel("internal", "internal");
bindLightingPanel("external", "external");
