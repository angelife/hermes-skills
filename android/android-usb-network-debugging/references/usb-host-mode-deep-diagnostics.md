# USB Host Mode Deep Diagnostics — Case Study: Mi8 (dipper)

## Device Profile

| Attribute | Value |
|-----------|-------|
| Device | Xiaomi Mi 8 (dipper) |
| SoC | Snapdragon 845 (SDM845) |
| Kernel | 4.9.337 (LineageOS 22 / Android 15) |
| USB Controller | DWC3 (a600000.ssusb) |
| PD PHY | PMI8998 (c440000.qcom,spmi:qcom,pmi8998@2:qcom,usb-pdphy@1700) |
| USB-C Speed | USB 2.0 only (480 Mbps, no SuperSpeed lines) |
| Target Device | AX88772D (0b95:1790) USB Ethernet Adapter |

## ❌ Incorrect Initial Diagnosis (Lesson: Verify nohup Survival First)

**First attempt**: Cleared dmesg with `dmesg -c`, started background capture via `adb shell "su -c 'nohup ... &'"`, physically swapped cables, read capture.

**Result**: Zero USB/extcon/dwc3/typec events. Only glgps/lhd init noise.

**False conclusion**: "Hardware detection interrupt never fired. CC line detection circuitry did not produce any kernel event."

**Actual root cause of the false negative**: The background capture process (the nohup'd sleep + dmesg) probably died when ADB shell terminated upon USB cable disconnect. The `nohup` invocation through `adb shell su -c` does NOT reliably protect child processes on mksh (Android's /system/bin/sh). The file existed but contained only init noise from the brief window before ADB dropped.

**Lesson**: A dmesg capture file existing ≠ the capture was running during the critical window. You MUST verify:
1. The nohup process tree actually survived ADB disconnect (use `pidof` before disconnecting)
2. The file's kernel timestamps span the expected period
3. The capture pattern `nohup sh -c "sleep N; dmesg > file" > /dev/null 2>&1 &` is the ONLY proven survivable pattern on mksh

## ✅ Corrected Diagnosis (Second Attempt — Proven Capture)

**Method**: Used the verified working pattern:
```bash
adb shell "su -c 'dmesg -c > /dev/null; nohup sh -c \"sleep 25; dmesg -c > /data/local/tmp/dmesg_cap3.txt\" > /dev/null 2>&1 &'"
```

The key difference: `nohup sh -c "...direct commands..."` (NOT a script file, NOT a separate .sh file - because executing a script adds an extra process layer that may not survive signal propagation on mksh).

**Capture result**: 434 lines, 33935 bytes, spanning ~70 seconds of kernel events.

### Full DWC3 Host Mode Activation Timeline

```
[2193.534]  usbpd usbpd0: USB Type-C disconnect         ← USB cable unplugged from Mac
[2193.536]  DWC3 in low power mode
[2193.538]  android_work: sent uevent USB_STATE=DISCONNECTED

[2197.461]  OTG_VOTER: val: 0
[2197.461]  usbpd usbpd0: Type-C Sink connected          ← AX88772D detected by PD PHY!

[2198.516]  DWC3 exited from low power mode              ← DWC3 wakes for host mode
[2198.518]  xhci-hcd: xHCI Host Controller               ← XHCI controller starts
[2198.518]  new USB bus registered, assigned bus number 1
[2198.523]  usb usb1: New USB device found (root hub)
[2198.525]  hub 1-0:1.0: 1 port detected
[2198.527]  xHCI Host Controller (bus 2)
[2198.525]  usb usb2: New USB device found (root hub)
[2198.526]  hub 2-0:1.0: 1 port detected

[2198.621]  usbpd: Error sending Source_Capabilities: -14  ← PD negotiation glitch (EAGAIN)

[... AX88772D was enumerated as usb 1-1, bound to ax88179_178a, eth0+eth1 created ...]

[2235.027]  usb 1-1: USB disconnect, device number 2     ← AX88772D being unplugged
[2235.028]  ax88179_178a 1-1:2.0 eth0: unregister        ← eth0 bound to WRONG driver
[2235.028]  ax88179_178a 1-1:2.1 eth1: unregister        ← eth1 bound to wrong driver
```

### Key Proof Points

| Event | Conclusion |
|-------|-----------|
| `Type-C Sink connected` | PD PHY (extcon4) CAN detect plugged devices |
| `DWC3 exited from low power mode` | DWC3 CAN transition out of peripheral mode |
| `xhci-hcd: xHCI Host Controller` | XHCI controller initializes successfully |
| `New USB device found` | USB devices are enumerated |
| `register 'ax88179_178a'` | Wrong driver claims 0b95:1790 — LAYER 2 issue |

### Why Initial Diagnosis was Wrong

The PD PHY DOES work. DWC3 DOES enter host mode. The fundamental issue is:

**Layer 2 (driver binding), NOT Layer 1 (host mode).**

The `ax88179_178a` driver has `0b95:1790` in its built-in id_table. The `asix` driver does NOT have it built-in (requires `new_id` registration). When the XHCI enumerates the device, the USB core's driver matching picks `ax88179_178a` first because:
1. Both drivers match 0b95:1790 (asix only if new_id was registered)
2. ax88179_178a is registered before asix in the kernel probe order
3. The USB core returns the first match, not the best match

### Phase 2: dmesg insertion capture (Corrected Procedure)

```bash
# ⚠️ CRITICAL: Use ONLY the proven nohup pattern
# DO NOT use: nohup script_file.sh &
# DO use:
adb shell "su -c '
  dmesg -c > /dev/null
  nohup sh -c \"sleep 25; dmesg > /data/local/tmp/dmesg_capture.txt\" > /dev/null 2>&1 &
  echo PID=$!
'"

# BEFORE disconnecting ADB, verify the process is running:
adb shell "su -c 'pidof sh | head -1'"
# Should show a PID — that is the nohup'd sh

# THEN physically swap cables (USB unplug → AX88772D plug)
# Wait at least 25 seconds
# Plug USB back

# Read the capture:
adb shell "su -c 'cat /data/local/tmp/dmesg_capture.txt | grep -iE \"usb|extcon|dwc3|typec|pmi8998|cc_state|id_state|hub|connect|disconnect|role|host|peripheral|new device|xhci|sink|source|pdphy|usbpd|eth0|eth1|carrier|register|low power\"'"
```

### dmesg Grep Keywords — Expanded Set

| Keyword | What it catches |
|---------|----------------|
| `usb` | All USB events |
| `extcon` | Extcon state changes |
| `dwc3` | DWC3 controller state transitions |
| `xhci` | XHCI host controller start/stop |
| `typec` | Type-C class events |
| `pmi8998` | PMIC events (charger/PD) |
| `cc_state` / `id_state` | CC/ID pin state |
| `hub` | Hub detection |
| `connect` / `disconnect` | USB connect/disconnect |
| `host` / `peripheral` | Mode transitions |
| `new device` | USB device enumeration |
| `sink` / `source` | Type-C role negotiation |
| `usbpd` | PD protocol messages |
| `registered` | Driver registration |
| `low power` | DWC3 power state transitions |
| `carrier` | Ethernet link state |
| `eth0` | Ethernet interface creation |
| `rmnet` | rmnet registration |
| `ax88179` / `asix` | Driver binding events |
| `-71` | USB protocol error (EPROTO) |

### Phase 3: extcon state

```bash
for e in /sys/class/extcon/extcon*/; do
  echo "== $(cat ${e}name) =="
  cat "${e}state"
done
```

Mi8/SD845 extcon mapping:

| Entry | Name | Meaning |
|-------|------|---------|
| extcon0 | ms-ext-disp | DisplayPort/HDMI alt mode — irrelevant |
| extcon1 | qcom,msm-eud | Embedded USB Debug — `USB=0` expected |
| extcon2 | qcom,qpnp-smb2 | Charger VBUS detection — `USB=0` on data-only cable |
| extcon3 | extcon_usb1 | Secondary USB controller |
| extcon4 | usb-pdphy | **PD PHY — KEY**: `USB_HOST=1` when host mode active |

### Phase 4: dual_role_usb state

```bash
cat /sys/class/dual_role_usb/otg_default/mode        # ufp (device) or dfp (host)
cat /sys/class/dual_role_usb/otg_default/data_role    # device or host
cat /sys/class/dual_role_usb/otg_default/power_role   # sink or source
cat /sys/class/dual_role_usb/otg_default/supported_modes
```

### Decision Tree (Updated)

```
/sys/class/typec/ exists?
├── YES → preferred_role writable? → A scheme viable (write PD PHY via Type-C class)
│               └── not writable → need i2c direct access (high risk)
└── NO  → Type-C class unavailable → A scheme has no legal software entry
          ↓
dmesg capture (using PROVEN nohup pattern) shows events?
├── YES — DWC3 exited low power + XHCI started + New USB device found
│   → Layer 1 WORKS! Problem is purely Layer 2 (driver binding)
│   → Solution: unbind + driver_override + rebind, or new_id + remove_id
│
├── YES — Type-C Sink/Source events but NO XHCI start → DWC3 role arbitration refused
│   → Try: OTG Y-cable, or independent powered hub
│
└── NO — zero events even with proven capture technique
    → TRUE hardware detection failure — CC detection circuit or bootloader locked
    → Use powered hub or different device
```

### What DOES Work on This Device (Corrected)

The Mi8 (dipper) with kernel 4.9.337 **CAN enter USB host mode via its Type-C port** when a USB device is physically plugged in. The PD PHY detects the device, DWC3 transitions to host mode, XHCI starts, and devices are enumerated.

The problem is purely at the **driver binding level**: the `ax88179_178a` driver (which has 0b95:1790 in its built-in id_table) claims the AX88772D before `asix` (which requires dynamic `new_id` registration) gets a chance.

**Solutions that work**:
1. **Pre-register + unbind/override/rebind**: Register 0b95:1790 with asix via `new_id`, then on device insertion, unbind ax88179_178a, set `driver_override=asix`, and rebind.
2. **remove_id probe**: Writing `0b95 1790` to `/sys/bus/usb/drivers/ax88179_178a/remove_id` returned exit 0 (may or may not actually remove built-in ID — needs further verification).
3. **Watchdog script**: A nohup'd loop that polls for AX88772D insertion and auto-fixes driver binding (see `references/ax88772d-driver-fix.md`).

## Key Architectural Notes

### DWC3 Mode Switching is extcon-Driven

`dwc3-msm.c` mode switching is driven by extcon notifier callbacks (extcon_id/extcon_vbus), NOT by direct sysfs mode file writes. Writing `host` to `/sys/devices/platform/soc/a600000.ssusb/mode` triggers `dwc3_otg_set_mode()` which is a soft trigger — it has no effect if the PD PHY (extcon4) hasn't reported `USB_HOST=1`.

The real switching happens when:
1. CC pin state changes (physical plug/unplug)
2. PMI8998 PD PHY detects the change and updates extcon state
3. extcon notifier fires → calls `dwc3_otg_notify()` → DWC3 transitions

### Verified DWC3 Power State Transitions

```
ADB USB plugged → DWC3 active (peripheral) → extcon4: USB=1 USB_HOST=0
   ↓ user unplugs USB
USB Type-C disconnect → DWC3 in low power mode → extcon4: USB=0
   ↓ user plugs AX88772D (sink device)
Type-C Sink connected → DWC3 exited from low power mode → XHCI starts → devices enumerate
   ↓ user unplugs device
USB disconnect → DWC3 in low power mode
```

### ax88179_178a has remove_id interface

`/sys/bus/usb/drivers/ax88179_178a/remove_id` exists and accepts writes:
```bash
echo "0b95 1790" > /sys/bus/usb/drivers/ax88179_178a/remove_id  # exit=0
```

Whether this actually removes the built-in ID (not just new_id-added IDs) is unverified. The kernel's `driver_override` mechanism is the more reliable approach.
