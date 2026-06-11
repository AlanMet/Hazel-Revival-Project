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
      title: "Open over HTTPS",
      message: "This page was opened as a local file.",
      hint: "Run apps/web/run.sh and open https://127.0.0.1:8765",
    };
  }

  if (!window.isSecureContext) {
    return {
      ok: false,
      title: "HTTPS required",
      message: "Web Bluetooth needs a secure connection.",
      hint: "Run apps/web/run.sh and open https://127.0.0.1:8765",
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

export const MACOS_UNSUPPORTED_MESSAGE =
  "macOS isn’t supported — Web Bluetooth can’t connect to the Zephyr on Mac. " +
  "Use an iPhone with Bluefy, or Chrome on Android.";
