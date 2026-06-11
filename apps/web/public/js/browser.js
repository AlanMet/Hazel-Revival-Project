/** Web Bluetooth: secure context + navigator.bluetooth. */

export function webBluetoothSupported() {
  return window.isSecureContext && typeof navigator.bluetooth !== "undefined";
}

function isIosDevice(ua = navigator.userAgent) {
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

export function isMacOs(ua = navigator.userAgent) {
  return /Mac OS X|Macintosh/.test(ua) && !isIosDevice(ua);
}

export function getEnvironment() {
  const ua = navigator.userAgent;
  return {
    href: location.href,
    secure: window.isSecureContext,
    hasBluetoothApi: typeof navigator.bluetooth !== "undefined",
    isIos: isIosDevice(ua),
    isMacOs: isMacOs(ua),
    userAgent: ua,
  };
}

export function getWebBluetoothStatus() {
  if (location.protocol === "file:") {
    return {
      ok: false,
      title: "Open via local server",
      message: "This page was opened as a local file.",
      hint: "Run apps/web/run.sh and open http://127.0.0.1:8765",
    };
  }

  if (!window.isSecureContext) {
    return {
      ok: false,
      title: "Localhost required",
      message: "Web Bluetooth needs a secure context (localhost or HTTPS).",
      hint: "Run apps/web/run.sh and open http://127.0.0.1:8765",
    };
  }

  if (typeof navigator.bluetooth === "undefined") {
    const env = getEnvironment();
    return {
      ok: false,
      title: "Web Bluetooth not available",
      message: "This browser does not expose navigator.bluetooth.",
      hint: env.isIos
        ? "On iPhone, install Bluefy and open this page inside it — not Safari."
        : "Try Chrome or Edge on Android, or Bluefy on iPhone.",
    };
  }

  return { ok: true };
}

export const MACOS_CONNECT_HINT =
  "On macOS, disconnect Razer Zephyr in System Settings → Bluetooth before connecting here. " +
  "If the browser picker fails, use the desktop app: ./apps/desktop/run.sh";
