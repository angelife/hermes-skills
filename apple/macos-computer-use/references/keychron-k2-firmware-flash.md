# Keychron K2 (White) — Firmware Flash via ISPCTool

An end-to-end example of using `computer_use` to flash firmware on a
Keychron K2 Special Edition keyboard via the ISPCTool macOS app.

## Pre-requisites

- Keychron K2 Special Edition (White backlight variant)
- USB-C data cable (NOT charge-only)
- Firmware zip from Keychron's special firmware page
- ISPCTool.app extracted and ready

## Bootloader mode

The keyboard must be in ISP/bootloader mode to accept a flash:

1. Disconnect any USB cable
2. Hold the **ESC** key
3. While holding ESC, plug the USB-C data cable into the Mac
4. Wait 2-3 seconds, then release ESC
5. The keyboard enumerates as VID 0x05ac / PID 0x024f (the same VID/PID
   used in normal Bluetooth mode, but accessible via USB)

Confirm with: `system_profiler SPUSBDataType | grep -A 10 Keychron`

Expected output:
```
Keychron K2:
  Product ID: 0x024f
  Vendor ID: 0x05ac (Apple Inc.)
  Speed: Up to 12 Mb/s
  Manufacturer: Keytron
```

## ISPCTool structure

The .app bundles firmware data inside `UserInfo.plist`:

```python
import plistlib
with open('K2-white-V1.6.app/Contents/Resources/UserInfo.plist', 'rb') as f:
    d = plistlib.load(f)
```

Key fields:
- `ISPFWData` — compressed dict with keys `compressed`, `data` (28384 bytes),
  `ratio` — the embedded hex firmware
- `ISPDeviceInfo` — `[{'pid': '0x024f', 'vid': '0x05ac'}]` — what to probe for
- `ISPSuccessMSG` — `"OK"` (appears in the UI when done)
- `ISPStartMSG` — `"Start update"` (appears during flash)
- `ISPStartBtn` — `"Stail"` (the Start button label)
- `ISPChipName` — `"SN32F26x"` (NXP chip on the K2)

## Flash procedure (computer_use)

1. Open ISPCTool.app (launch or open the .app)
2. Capture to verify window is visible:

   ```
   computer_use(action="capture", mode="som", app="ISPCTool")
   ```

3. **Important**: focus the app before clicking, or AXPress may not
   register:

   ```
   computer_use(action="focus_app", app="ISPCTool")
   ```

   Note: the binary name is `ISPCTool` (from Contents/MacOS/ISPCTool),
   NOT the window title `K2-white-V1.6`.

4. Click the Start button:

   ```
   computer_use(action="click", element=1, capture_after=True)
   ```

5. Monitor progress by re-capturing every few seconds. The button label
   "Stail" stays present but the progress bar and status text change.
   Use `mode="vision"` if SOM shows no AX tree change — the vision model
   can detect "Start update" in progress text and "OK" on completion.

6. When the UI shows "OK" and the progress bar is full, the flash is
   complete.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "No compatible device found" | Keyboard not in bootloader mode | Hold ESC while plugging USB |
| Button click returns ok=true but no effect | App window not focused | `focus_app("ISPCTool")` first |
| USB shows Mac internal keyboard only | Cable is charge-only | Use a data-capable USB-C cable |
| ISPCTool window black in capture | App on different Space | Works anyway — cua-driver drives all Spaces |
| `ISPFWData` shows "3 chars" | Wrong Python parsing of plist dict | Parse as dict, not str — it has `data`, `compressed`, `ratio` keys |
| "Fail" after Start | Keyboard disconnected mid-flash | Re-enter bootloader mode and retry |
