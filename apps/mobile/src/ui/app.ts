import { ZephyrClient } from "../protocol/client.js";
import type { DeviceState } from "../protocol/parse.js";
import type { FanSpeed } from "../protocol/constants.js";
import { WAVE_RATE_FAST, WAVE_RATE_MEDIUM } from "../protocol/constants.js";

type Screen = "connect" | "dashboard" | "control";

export class App {
  private client = new ZephyrClient();
  private screen: Screen = "connect";
  private devices: { deviceId: string; name: string }[] = [];
  private selectedId: string | null = null;
  private controlZone: "fan" | "internal" | "external" | null = null;
  private status = "";

  constructor(
    private root: HTMLElement,
    private statusEl: HTMLElement,
  ) {}

  async init(): Promise<void> {
    await this.client.initialize();
    this.client.setFanNotifyHandler((speed) => {
      this.setStatus(`Fan changed on mask: ${speed}`);
      void this.refreshState();
    });
    this.render();
  }

  private setStatus(msg: string): void {
    this.status = msg;
    this.statusEl.textContent = msg;
  }

  private async refreshState(): Promise<void> {
    try {
      await this.client.syncState();
      this.render();
    } catch (e) {
      this.setStatus(String(e));
    }
  }

  private render(): void {
    this.root.innerHTML = "";
    if (this.screen === "connect") this.renderConnect();
    else if (this.screen === "dashboard") this.renderDashboard();
    else if (this.screen === "control") this.renderControl();
  }

  private renderConnect(): void {
    const title = el("h1", "Connect Zephyr");
    const hint = el(
      "p",
      "Scan for your mask, select it, then connect. Bluetooth permission is required.",
    );
    hint.className = "muted";

    const scanBtn = button("Scan", () => void this.onScan());
    const connectBtn = button("Connect", () => void this.onConnect());
    connectBtn.disabled = !this.selectedId;

    const list = document.createElement("ul");
    list.className = "device-list";
    for (const dev of this.devices) {
      const item = document.createElement("li");
      item.className = this.selectedId === dev.deviceId ? "selected" : "";
      item.textContent = dev.name;
      item.onclick = () => {
        this.selectedId = dev.deviceId;
        this.render();
      };
      list.appendChild(item);
    }

    this.root.append(title, hint, row(scanBtn, connectBtn), list);
  }

  private renderDashboard(): void {
    const state = this.client.lastState;
    const title = el("h1", "Zephyr");
    const battery = el(
      "p",
      `Battery: ${state?.batteryPercent ?? "—"}%${
        state?.isCharging ? " (charging)" : ""
      }`,
    );
    battery.className = "accent";
    const fw = state?.firmwareVersion
      ? el("p", `Firmware ${state.firmwareVersion}`)
      : null;
    if (fw) fw.className = "muted small";

    const fanRow = dashboardRow("Fan speed", formatFan(state), () => {
      this.controlZone = "fan";
      this.screen = "control";
      this.render();
    });
    const intRow = dashboardRow(
      "Internal lighting",
      state?.internalEffect ?? "—",
      () => {
        this.controlZone = "internal";
        this.screen = "control";
        this.render();
      },
    );
    const extRow = dashboardRow(
      "External lighting",
      state?.externalEffect ?? "—",
      () => {
        this.controlZone = "external";
        this.screen = "control";
        this.render();
      },
    );

    const refreshBtn = button("Refresh", () => void this.refreshState());
    const disconnectBtn = button("Disconnect", () => void this.onDisconnect());

    const nodes: Node[] = [title, battery];
    if (fw) nodes.push(fw);
    nodes.push(fanRow, intRow, extRow, row(refreshBtn, disconnectBtn));
    this.root.append(...nodes);
  }

  private renderControl(): void {
    const back = button("← Back", () => {
      this.screen = "dashboard";
      this.controlZone = null;
      this.render();
    });
    const title = el("h2", zoneTitle(this.controlZone));
    this.root.append(back, title);

    const grid = document.createElement("div");
    grid.className = "btn-grid";

    if (this.controlZone === "fan") {
      for (const [label, fn] of [
        ["Low", () => this.client.fanLow()],
        ["High", () => this.client.fanHigh()],
        ["Off", () => this.client.fanOff()],
      ] as const) {
        grid.appendChild(button(label, () => void this.runCommand(fn)));
      }
    } else if (this.controlZone === "internal") {
      grid.appendChild(
        button("Static (red)", () =>
          void this.runCommand(() => this.client.internalStatic(255, 0, 0)),
        ),
      );
      grid.appendChild(
        button("Spectrum", () => void this.runCommand(() => this.client.internalSpectrum())),
      );
      grid.appendChild(
        button("Breathing", () => void this.runCommand(() => this.client.internalBreathing())),
      );
      grid.appendChild(
        button("Off", () => void this.runCommand(() => this.client.internalOff())),
      );
    } else if (this.controlZone === "external") {
      grid.appendChild(
        button("Static (blue)", () =>
          void this.runCommand(() => this.client.externalStatic(0, 0, 255)),
        ),
      );
      grid.appendChild(
        button("Spectrum", () => void this.runCommand(() => this.client.externalSpectrum())),
      );
      grid.appendChild(
        button("Breathing", () => void this.runCommand(() => this.client.externalBreathing())),
      );
      grid.appendChild(
        button("Wave LTR", () =>
          void this.runCommand(() =>
            this.client.externalWave(true, WAVE_RATE_MEDIUM),
          ),
        ),
      );
      grid.appendChild(
        button("Wave fast", () =>
          void this.runCommand(() => this.client.externalWave(true, WAVE_RATE_FAST)),
        ),
      );
      grid.appendChild(
        button("Off", () => void this.runCommand(() => this.client.externalOff())),
      );
    }

    this.root.appendChild(grid);
  }

  private async onScan(): Promise<void> {
    this.setStatus("Scanning…");
    try {
      this.devices = await this.client.scan();
      this.selectedId = this.devices[0]?.deviceId ?? null;
      this.setStatus(this.devices.length ? `Found ${this.devices.length}` : "No devices");
      this.render();
    } catch (e) {
      this.setStatus(String(e));
    }
  }

  private async onConnect(): Promise<void> {
    if (!this.selectedId) return;
    this.setStatus("Connecting…");
    try {
      await this.client.connect(this.selectedId);
      this.screen = "dashboard";
      this.setStatus("Connected");
      this.render();
    } catch (e) {
      this.setStatus(String(e));
    }
  }

  private async onDisconnect(): Promise<void> {
    await this.client.disconnect();
    this.screen = "connect";
    this.setStatus("Disconnected");
    this.render();
  }

  private async runCommand(fn: () => Promise<boolean>): Promise<void> {
    this.setStatus("Sending…");
    const ok = await fn();
    if (ok) {
      await this.refreshState();
      this.setStatus("OK");
    } else {
      this.setStatus("No device ack");
    }
  }
}

function formatFan(state: DeviceState | null): string {
  if (!state) return "—";
  const labels: Record<FanSpeed, string> = { off: "Off", low: "Low", high: "High" };
  return labels[state.fanSpeed] ?? state.fanSpeed;
}

function zoneTitle(zone: string | null): string {
  if (zone === "fan") return "Fan speed";
  if (zone === "internal") return "Internal lighting";
  if (zone === "external") return "External lighting";
  return "Control";
}

function el(tag: string, text: string): HTMLElement {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

function button(label: string, onClick: () => void): HTMLButtonElement {
  const btn = document.createElement("button");
  btn.textContent = label;
  btn.type = "button";
  btn.onclick = onClick;
  return btn;
}

function row(...nodes: HTMLElement[]): HTMLElement {
  const div = document.createElement("div");
  div.className = "row";
  div.append(...nodes);
  return div;
}

function dashboardRow(label: string, detail: string, onClick: () => void): HTMLElement {
  const row = document.createElement("button");
  row.type = "button";
  row.className = "dashboard-row";
  const left = el("span", label);
  const right = el("span", detail);
  right.className = "muted";
  row.append(left, right);
  row.onclick = onClick;
  return row;
}
