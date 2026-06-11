# Zephyr Controller (mobile)

Capacitor + TypeScript app for iOS and Android.

## Build web assets

```bash
npm install
npm run build
```

## Run on device

```bash
npx cap add android   # first time
npx cap add ios       # first time (macOS only)
npm run cap:sync
npx cap open android
```

## Bluetooth permissions

**Android** (`android/app/src/main/AndroidManifest.xml`):

- `BLUETOOTH_SCAN` (with `usesPermissionFlags="neverForLocation"` on API 31+)
- `BLUETOOTH_CONNECT`
- `ACCESS_FINE_LOCATION` (required for scan on older APIs)

**iOS** (`ios/App/App/Info.plist`):

- `NSBluetoothAlwaysUsageDescription` — explain why the app needs Bluetooth.
