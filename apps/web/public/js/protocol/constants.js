/** GATT UUIDs and protocol constants (from reverse-engineering reference). */

export const DEVICE_NAME_PREFIXES = ["Razer Zephyr", "Zephyr"];

/** macOS / paired devices often show suffixes like "Razer Zephyr - paired". */
export function isZephyrDeviceName(name) {
  return typeof name === "string" && name.trim().length > 0 && name.toLowerCase().includes("zephyr");
}

/** BLE picker sometimes returns a MAC/UUID instead of a friendly name. */
export function formatDisplayDeviceName(name) {
  if (isZephyrDeviceName(name)) return name.trim();
  return "Razer Zephyr";
}

export const GAP_SERVICE = "00001800-0000-1000-8000-00805f9b34fb";
export const GAP_DEVICE_NAME_CHAR = "00002a00-0000-1000-8000-00805f9b34fb";

export const RAZER_VENDOR_SERVICE = "52401523-f97c-7f90-0e7f-6c6f4e36db1c";
export const RAZER_VENDOR_WRITE = "52401524-f97c-7f90-0e7f-6c6f4e36db1c";
export const RAZER_VENDOR_NOTIFY = "52401525-f97c-7f90-0e7f-6c6f4e36db1c";
export const RAZER_VENDOR_NOTIFY_EXTRA = "52401526-f97c-7f90-0e7f-6c6f4e36db1c";
export const BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb";

export const EXTERNAL_LIGHT_ZONE = 0x05;
export const INTERNAL_LIGHT_ZONE = 0x01;

export const NOTIFY_TIMEOUT_MS = 1500;
export const STATUS_SUCCESS = 0x02;
export const REQUEST_ID_START = 0x30;
