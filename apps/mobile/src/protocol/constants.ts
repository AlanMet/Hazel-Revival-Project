/** Razer Zephyr GATT identifiers — mirrors docs/config/gatt_map.yaml */

export const DEVICE_NAME_PATTERNS = ["Zephyr", "Razer", "Hazel"];

export const RAZER_VENDOR_SERVICE = "52401523-F97C-7F90-0E7F-6C6F4E36DB1C";
export const RAZER_VENDOR_WRITE = "52401524-F97C-7F90-0E7F-6C6F4E36DB1C";
export const RAZER_VENDOR_NOTIFY = "52401525-F97C-7F90-0E7F-6C6F4E36DB1C";
export const RAZER_VENDOR_NOTIFY_EXTRA = "52401526-F97C-7F90-0E7F-6C6F4E36DB1C";
export const BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb";

export const EXTERNAL_LIGHT_ZONE = 0x05;
export const INTERNAL_LIGHT_ZONE = 0x01;

export const STATUS_SUCCESS = 0x02;
export const NOTIFY_TIMEOUT_MS = 1500;
export const REQUEST_ID_START = 0x30;

export const WAVE_RATE_FACTORY = 90;
export const WAVE_RATE_SLOW = 15;
export const WAVE_RATE_MEDIUM = 50;
export const WAVE_RATE_FAST = 100;

export type FanSpeed = "off" | "low" | "high";

export const FAN_LEVEL: Record<FanSpeed, number> = {
  off: 0,
  low: 1,
  high: 2,
};
