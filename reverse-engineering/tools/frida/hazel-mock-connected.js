/**
 * Mock a paired + connected Razer Zephyr (Hazel) for UI exploration in the emulator.
 * No BLE required — dashboard + chroma picker use in-memory device state.
 */

function seedHazel(mgr) {
  if (mgr === null) {
    return false;
  }
  const Hazel = Java.use('com.razer.audiocompanion.model.devices.Hazel');
  const ArrayList = Java.use('java.util.ArrayList');
  const System = Java.use('java.lang.System');
  const Boolean = Java.use('java.lang.Boolean');

  const list = mgr.allAudioDevices.value;
  if (list.size() > 0) {
    return true;
  }

  const hazel = Hazel.$new();
  hazel.address.value = 'DE:AD:BE:EF:00:01';
  hazel.isActive.value = Boolean.valueOf(true);
  hazel.isPrimary.value = true;
  hazel.requirePair.value = Boolean.valueOf(false);
  hazel.connectionStatus.value = 2;
  hazel.fanSpeedValue.value = 0;
  hazel.lastFanSpeedUpdate.value = System.currentTimeMillis();

  const devices = ArrayList.$new();
  devices.add(hazel);
  mgr.saveAudioDevice(devices);
  console.log('[hazel-mock] Seeded mock Hazel device (paired + connected)');
  return true;
}

function hookBleAdapterIsConnected(RazerBleAdapter) {
  RazerBleAdapter.isConnected.overload().implementation = function () {
    return true;
  };
  RazerBleAdapter.isConnected.overload('java.lang.String').implementation = function (_addr) {
    return true;
  };
  RazerBleAdapter.isConnected.overload('java.util.List').implementation = function (_list) {
    return true;
  };
  RazerBleAdapter.isConnecting.overload('java.lang.String').implementation = function (_addr) {
    return false;
  };
  RazerBleAdapter.connectDeviceListString.overload(
    'java.util.List',
    'long',
    'boolean',
    'boolean'
  ).implementation = function (_addrs, _timeout, _a, _b) {
    return Java.use('java.util.ArrayList').$new();
  };
}

let hooksInstalled = false;

function installHooks() {
  if (hooksInstalled) {
    return true;
  }
  const RDM = Java.use('com.razer.audiocompanion.manager.RazerDeviceManager');
  const mgr = RDM.getInstance();
  if (mgr === null) {
    console.log('[hazel-mock] Manager not ready yet');
    return false;
  }

  seedHazel(mgr);

  RDM.isConnected.overload().implementation = function () {
    try {
      seedHazel(RDM.getInstance());
    } catch (_e) {}
    return true;
  };
  RDM.isConnected.overload(
    'com.razer.audiocompanion.model.devices.BluetoothDevice'
  ).implementation = function (_dev) {
    return true;
  };
  RDM.isConnecting.implementation = function () {
    return false;
  };
  RDM.connect.overload(
    'com.razer.audiocompanion.model.devices.BluetoothDevice',
    'boolean'
  ).implementation = function (_dev, _reconnect) {
    try {
      seedHazel(RDM.getInstance());
    } catch (_e) {}
    return true;
  };

  const RazerBleAdapter = Java.use('com.razer.commonbluetooth.base.ble.RazerBleAdapter');
  hookBleAdapterIsConnected(RazerBleAdapter);

  const Hazel = Java.use('com.razer.audiocompanion.model.devices.Hazel');
  Hazel.updateFanSpeed.implementation = function (_adapter) {
    this.fanSpeedValue.value = 0;
    this.lastFanSpeedUpdate.value = Java.use('java.lang.System').currentTimeMillis();
    return true;
  };
  Hazel.applyFirmwareEffect.implementation = function (_adapter, _effect) {
    return true;
  };
  Hazel.applyBrightness.implementation = function (_adapter, _zone, _level) {
    return true;
  };

  hooksInstalled = true;
  console.log('[hazel-mock] Hooks active — explore Internal/External lighting, Fan, Buy Filters');
  return true;
}

function tryInstallWithRetry(attempt) {
  Java.perform(function () {
    if (installHooks()) {
      return;
    }
    if (attempt < 20) {
      setTimeout(function () {
        tryInstallWithRetry(attempt + 1);
      }, 500);
    } else {
      console.log('[hazel-mock] Gave up waiting for RazerDeviceManager');
    }
  });
}

Java.perform(function () {
  tryInstallWithRetry(0);
});
