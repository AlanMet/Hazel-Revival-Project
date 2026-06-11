/** DOM wiring — walkthrough, mask hotspots, control dock. */

import {
  getEnvironment,
  getWebBluetoothStatus,
  MACOS_UNSUPPORTED_MESSAGE,
} from "./browser.js";
import { clearConnectLog, connectLog } from "./connect-log.js";
import { formatDisplayDeviceName } from "./protocol/constants.js";
import { APP_VERSION } from "./version.js";

const ZONE_TITLES = {
  fan: "Fan speed",
  internal: "Internal lighting",
  external: "External lighting",
};

const COLOR_DEBOUNCE_MS = 180;

function parseHexColor(hex) {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function bindUi(orchestrator, elements) {
  const status = getWebBluetoothStatus();

  const {
    viewUnsupported,
    viewOnboarding,
    viewControl,
    errorMessage,
    errorHint,
    errorTitle,
    errorSteps,
    statusEl,
    phasePair,
    phaseConnect,
    nextPairBtn,
    connectBtn,
    connectAllBtn,
    disconnectBtn,
    deviceNameEl,
    hotspots,
    dock,
    dockTitle,
    dockBody,
    dockClose,
    diagEl,
    platformNoticeMacos,
    templates,
  } = elements;

  let submenus = [];
  let activeZone = null;
  const colorTimers = new WeakMap();
  let colorSendChain = Promise.resolve();

  function setStatus(message) {
    if (statusEl) statusEl.textContent = message ?? "";
  }

  function formatDebugLines(debug) {
    if (!debug?.length) return [];
    return [
      "",
      "--- Connect debug (latest attempt) ---",
      ...debug.map((entry) => {
        const parts = [`[${entry.step}]`];
        if (entry.elapsed) parts.push(entry.elapsed);
        if (entry.phase) parts.push(`phase=${entry.phase}`);
        if (entry.name) parts.push(`name=${JSON.stringify(entry.name)}`);
        if (entry.deviceName) parts.push(`device=${JSON.stringify(entry.deviceName)}`);
        if (entry.deviceId) parts.push(`id=${entry.deviceId}`);
        if (entry.errorName) parts.push(`err=${entry.errorName}`);
        if (entry.errorMessage) parts.push(JSON.stringify(entry.errorMessage));
        if (entry.service) parts.push(`service=${entry.service}`);
        if (entry.connected != null) parts.push(`connected=${entry.connected}`);
        if (entry.gattConnected != null) parts.push(`gatt=${entry.gattConnected}`);
        if (entry.zephyrMatch != null) parts.push(`zephyrMatch=${entry.zephyrMatch}`);
        if (entry.acceptAll != null) parts.push(`acceptAll=${entry.acceptAll}`);
        return parts.join(" ");
      }),
    ];
  }

  function showDiagnostics(connectDebug = null) {
    if (!diagEl) return;
    const e = getEnvironment();
    const gate = getWebBluetoothStatus();
    diagEl.textContent = [
      `Version: v${APP_VERSION}`,
      `URL: ${e.href}`,
      `Secure context: ${e.secure}`,
      `navigator.bluetooth: ${e.hasBluetoothApi ? "yes" : "no"}`,
      `Gate: ${gate.ok ? "open" : gate.title}`,
      `macOS: ${e.isMacOs ? "yes" : "no"}`,
      `iOS: ${e.isIos ? "yes" : "no"}`,
      ...formatDebugLines(connectDebug),
    ].join("\n");
  }

  function showMacOsNotice() {
    const env = getEnvironment();
    if (!platformNoticeMacos) return;
    if (env.isMacOs) {
      platformNoticeMacos.hidden = false;
      platformNoticeMacos.textContent = MACOS_UNSUPPORTED_MESSAGE;
      setConnectButtonsDisabled(true);
    } else {
      platformNoticeMacos.hidden = true;
    }
  }

  function showUnsupported(s) {
    if (viewUnsupported) viewUnsupported.hidden = false;
    if (viewOnboarding) viewOnboarding.hidden = true;
    if (viewControl) viewControl.hidden = true;
    if (errorTitle) errorTitle.textContent = s.title ?? "Browser not supported";
    if (errorMessage) errorMessage.textContent = s.message;
    if (errorHint) errorHint.textContent = s.hint ?? "";
    if (errorSteps) {
      errorSteps.replaceChildren(
        ...(s.steps ?? []).map((step) => {
          const li = document.createElement("li");
          li.textContent = step;
          return li;
        }),
      );
    }
  }

  function setSetupStep(step) {
    if (viewOnboarding) viewOnboarding.dataset.step = String(step);
    for (const item of viewOnboarding?.querySelectorAll(".setup-progress__item") ?? []) {
      const n = Number(item.dataset.step);
      item.classList.toggle("is-active", n === step);
      item.classList.toggle("is-done", n < step);
    }
  }

  function setConnectButtonsDisabled(disabled) {
    if (connectBtn) connectBtn.disabled = disabled;
    if (connectAllBtn) connectAllBtn.disabled = disabled;
  }

  function resetWalkthrough() {
    if (phasePair) phasePair.hidden = false;
    if (phaseConnect) phaseConnect.hidden = true;
    setConnectButtonsDisabled(false);
    setSetupStep(1);
  }

  function showOnboarding() {
    if (viewUnsupported) viewUnsupported.hidden = true;
    if (viewOnboarding) viewOnboarding.hidden = false;
    if (viewControl) viewControl.hidden = true;
    resetWalkthrough();
    showMacOsNotice();
  }

  function showControl(name) {
    if (viewUnsupported) viewUnsupported.hidden = true;
    if (viewOnboarding) viewOnboarding.hidden = true;
    if (viewControl) viewControl.hidden = false;
    if (deviceNameEl) deviceNameEl.textContent = formatDisplayDeviceName(name);
  }

  function goToConnectPhase() {
    if (phasePair) phasePair.hidden = true;
    if (phaseConnect) phaseConnect.hidden = false;
    setSetupStep(2);
    setStatus("");
  }

  // --- Onboarding (register first) ---
  nextPairBtn?.addEventListener("click", () => {
    goToConnectPhase();
  });

  async function onConnectClick({ acceptAll = false } = {}) {
    if (getEnvironment().isMacOs) {
      setStatus(MACOS_UNSUPPORTED_MESSAGE);
      return;
    }
    clearConnectLog();
    connectLog(`ui: Connect clicked (acceptAll=${acceptAll})`);
    setStatus("Connecting…");
    setConnectButtonsDisabled(true);
    try {
      connectLog("ui: calling orchestrator.connect…");
      const result = await orchestrator.connect({ acceptAll });
      connectLog(`ui: connect returned ok=${result.ok}`);
      showDiagnostics(result.debug);
      document.querySelector(".diag-wrap")?.setAttribute("open", "");
      if (!result.ok && !result.debug?.length) {
        connectLog("ui: no debug entries — connect may not have run");
      }
      setStatus(result.message);
      if (result.ok) {
        showControl(orchestrator.deviceName);
      } else {
        setConnectButtonsDisabled(false);
      }
    } catch (err) {
      connectLog(`ui: unexpected throw — ${err instanceof Error ? err.message : String(err)}`);
      showDiagnostics(orchestrator.lastDebug ?? null);
      document.querySelector(".diag-wrap")?.setAttribute("open", "");
      setStatus(err instanceof Error ? err.message : String(err));
      setConnectButtonsDisabled(false);
    }
  }

  connectBtn?.addEventListener("click", () => onConnectClick());
  connectAllBtn?.addEventListener("click", () => onConnectClick({ acceptAll: true }));

  disconnectBtn?.addEventListener("click", async () => {
    await orchestrator.disconnect();
    closeDock();
    showOnboarding();
    setStatus("");
  });

  showDiagnostics();
  showMacOsNotice();
  connectLog("ui: bindUi finished");

  if (!status.ok) {
    showUnsupported(status);
    return;
  }

  showOnboarding();
  setSetupStep(1);

  // --- Mask controls ---
  function bindControlHandlers(root) {
    for (const btn of root.querySelectorAll(".effect-btn")) {
      btn.addEventListener("click", () => onEffectClick(btn));
    }
    for (const btn of root.querySelectorAll(".wave-btn")) {
      btn.addEventListener("click", () => onWaveClick(btn));
    }
    for (const input of root.querySelectorAll(".live-color")) {
      bindLiveColor(input);
    }
    submenus = [...root.querySelectorAll(".submenu")];
  }

  function hideSubmenusExcept(id) {
    for (const menu of submenus) {
      menu.classList.toggle("hidden", menu.id !== id);
    }
  }

  function setActiveChip(group, button) {
    for (const btn of dockBody.querySelectorAll(
      `.toggles[data-group="${group}"] .effect-btn`,
    )) {
      btn.classList.toggle("active", btn === button);
    }
  }

  function setActiveWaveSpeed(button) {
    for (const btn of dockBody.querySelectorAll(".wave-btn")) {
      btn.classList.toggle("active", btn === button);
    }
  }

  async function runAction(action, args, { group, activeBtn, speedBtn, silent = false } = {}) {
    if (!orchestrator[action]) return { ok: false };

    if (!silent) {
      setStatus("Sending…");
      dockBody.querySelectorAll("button").forEach((b) => (b.disabled = true));
    }

    try {
      const result = await orchestrator[action](...args);
      if (!silent) setStatus(result.message);
      if (result.ok && activeBtn) setActiveChip(group, activeBtn);
      if (result.ok && speedBtn) setActiveWaveSpeed(speedBtn);
      return result;
    } catch (err) {
      if (!silent) {
        setStatus(err instanceof Error ? err.message : String(err));
      }
      return { ok: false };
    } finally {
      if (!silent) {
        dockBody.querySelectorAll("button").forEach((b) => (b.disabled = false));
      }
    }
  }

  function queueColorSend(input) {
    const action = input.dataset.action;
    const submenu = input.closest(".submenu");
    const group = submenu?.dataset.group;
    const staticBtn = dockBody.querySelector(
      `.effect-btn[data-opens="${submenu?.id}"]`,
    );
    const [r, g, b] = parseHexColor(input.value);

    colorSendChain = colorSendChain
      .then(() => runAction(action, [r, g, b], { group, activeBtn: staticBtn, silent: true }))
      .then((result) => {
        if (!result?.ok) setStatus(`${action} — no device ack`);
      })
      .catch((err) => {
        setStatus(err instanceof Error ? err.message : String(err));
      });
  }

  function bindLiveColor(input) {
    input.addEventListener("input", () => {
      clearTimeout(colorTimers.get(input));
      colorTimers.set(
        input,
        setTimeout(() => queueColorSend(input), COLOR_DEBOUNCE_MS),
      );
    });
  }

  function sendLiveColorNow(submenuId) {
    const input = dockBody.querySelector(`#${submenuId} .live-color`);
    if (input) queueColorSend(input);
  }

  async function onEffectClick(btn) {
    const group = btn.closest(".toggles")?.dataset.group;
    const submenuId = btn.dataset.opens;

    if (submenuId) {
      hideSubmenusExcept(submenuId);
      document.getElementById(submenuId)?.classList.remove("hidden");
      setActiveChip(group, btn);
      if (submenuId.endsWith("-static")) sendLiveColorNow(submenuId);
      return;
    }

    hideSubmenusExcept(null);
    for (const btn of dockBody.querySelectorAll(".wave-btn")) {
      btn.classList.remove("active");
    }
    const action = btn.dataset.action;
    if (action) await runAction(action, [], { group, activeBtn: btn });
  }

  async function onWaveClick(btn) {
    const rate = Number(btn.dataset.waveRate);
    const group = btn.closest(".submenu")?.dataset.group ?? "external";
    const waveBtn = dockBody.querySelector('.effect-btn[data-opens="external-wave"]');
    await runAction("externalWave", [rate], { group, activeBtn: waveBtn, speedBtn: btn });
  }

  function openZone(zone) {
    activeZone = zone;
    for (const h of hotspots) {
      h.classList.toggle("active", h.dataset.zone === zone);
    }

    const tpl = templates[zone];
    if (!tpl) return;

    dockTitle.textContent = ZONE_TITLES[zone] ?? zone;
    dockBody.innerHTML = "";
    dockBody.appendChild(tpl.content.cloneNode(true));
    dock.hidden = false;
    colorSendChain = Promise.resolve();
    bindControlHandlers(dockBody);
    hideSubmenusExcept(null);
    setStatus("");
  }

  function closeDock() {
    if (dock) dock.hidden = true;
    activeZone = null;
    for (const h of hotspots) h.classList.remove("active");
  }

  for (const h of hotspots) {
    h.addEventListener("click", () => {
      if (!orchestrator.isConnected) return;
      if (activeZone === h.dataset.zone && dock && !dock.hidden) {
        closeDock();
      } else {
        openZone(h.dataset.zone);
      }
    });
  }

  dockClose?.addEventListener("click", closeDock);
}
