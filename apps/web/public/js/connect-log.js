/** Visible connect log + console.log (console.debug is hidden by default in Chrome). */

export function connectLog(message) {
  const line = `[${new Date().toISOString().slice(11, 19)}] ${message}`;
  console.log("[Hazel]", message);

  const el = document.getElementById("connect-log");
  if (!el) return;
  el.hidden = false;
  el.textContent += `${line}\n`;
  el.scrollTop = el.scrollHeight;
}

export function clearConnectLog() {
  const el = document.getElementById("connect-log");
  if (!el) return;
  el.textContent = "";
  el.hidden = true;
}
