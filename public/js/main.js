import { connectLog } from "./connect-log.js";
import { BluetoothTransport } from "./bluetooth.js";
import { ZephyrOrchestrator } from "./orchestrator.js";
import { bindUi } from "./ui.js";

const orchestrator = new ZephyrOrchestrator(new BluetoothTransport());
connectLog("main: modules loaded");

try {
  bindUi(orchestrator, {
    viewUnsupported: document.getElementById("view-unsupported"),
    viewOnboarding: document.getElementById("view-onboarding"),
    viewControl: document.getElementById("view-control"),
    errorMessage: document.getElementById("error-message"),
    errorHint: document.getElementById("error-hint"),
    errorTitle: document.getElementById("error-title"),
    errorSteps: document.getElementById("error-steps"),
    statusEl: document.getElementById("status"),
    phasePair: document.getElementById("phase-pair"),
    phaseConnect: document.getElementById("phase-connect"),
    nextPairBtn: document.getElementById("next-pair"),
    connectBtn: document.getElementById("connect"),
    connectAllBtn: document.getElementById("connect-all"),
    disconnectBtn: document.getElementById("disconnect"),
    deviceNameEl: document.getElementById("device-name"),
    hotspots: document.querySelectorAll(".zone"),
    dock: document.getElementById("dock"),
    dockTitle: document.getElementById("dock-title"),
    dockBody: document.getElementById("dock-body"),
    dockClose: document.getElementById("dock-close"),
    diagEl: document.getElementById("diag"),
    platformNoticeMacos: document.getElementById("platform-notice-macos"),
    templates: {
      fan: document.getElementById("tpl-fan"),
      internal: document.getElementById("tpl-internal"),
      external: document.getElementById("tpl-external"),
    },
  });
} catch (err) {
  console.error(err);
  const status = document.getElementById("status");
  if (status) {
    status.textContent =
      err instanceof Error ? `App error: ${err.message}` : "App failed to load.";
  }
}
