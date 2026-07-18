# Mi8 USB-C Ethernet Quirks

## Symptom
- With USB-C Ethernet adapter attached: no `eth0`, no host IP, and USB ADB may become unstable or disappear.
- `adb devices` sometimes shows device, but `adb shell` drops immediately.

## Verified Cause
- `/sys/bus/usb/devices` may be empty for that USB-C Ethernet adapter.
- `logcat`/`dmesg` show no usb/ethernet/adbd events when adapter is plugged in.
- In this state the adapter is **not enumerated at all** on Mi8 / MIUI, so it is not just stealing the bus; it is invisible.

## Workaround
- Prefer a **USB-C HUB**: one USB-A to Mac for ADB, one port to the Ethernet adapter.
- If HUB is unavailable, rely on **TCP/IP ADB** set up while USB is still connected:
  - `adb shell 'su 0 -c "setprop service.adb.tcp.port 5555; stop adbd; start adbd"'`
  - Then unplug USB and `adb connect 192.168.1.26:5555`
- If USB is already lost and Ethernet is unavailable, re-plug USB to recover ADB.
- Do not assume "网卡连不上" equals router/host blocking; first check whether Android actually created a network interface.

## Diagnostic Sequence
1. `adb shell 'su 0 -c "ip link show"'` — look for `eth0`, `enp*`, `enx*`
2. `adb shell 'su 0 -c "ls /sys/bus/usb/devices"'` — empty means no USB device enumeration
3. `adb shell 'su 0 -c "dmesg | tail -n 80"'` — search for usb/ethernet/adbd
4. Only after confirming enumeration, then check Mac reachability and `adb connect`
