# Synaptics touchscreen — Mi6 (Xiaomi Mi 6 / sagit)

## Device info

- Device: Xiaomi Mi 6 (sagit), LineageOS 22.2 / Android 15, Magisk root
- Touch controller: Synaptics `synaptics_dsi_force` driver
- I2C address: 0x20 on i2c-5 (`/sys/bus/i2c/devices/5-0020`)
- Input event: event1
- Sysfs path: `/sys/devices/soc/c179000.i2c/i2c-5/5-0020/input/input1/`

## irq_enable — NOT available on LineageOS 22.2

**Important discrepancy**: The `irq_enable` sysfs file described here is available on some kernel configurations/driver builds, but **NOT** on the current device (Mi6 / sagit / LineageOS 22.2 / Android 15). On LineageOS 22.2, `/sys/bus/i2c/devices/5-0020/input/input2/` does NOT contain `irq_enable`.

For LineageOS 22.2, use I2C driver unbind instead (see `references/mi6-synaptics-touch.md`).

### When irq_enable IS available

All three paths point to the same file (hard link in sysfs):

1. `/sys/bus/i2c/devices/5-0020/input/input1/irq_enable` (shortest, preferred)
2. `/sys/devices/soc/c179000.i2c/i2c-5/5-0020/input/input1/irq_enable` (full)
3. `/sys/bus/i2c/drivers/synaptics_dsi_force/5-0020/input/input1/irq_enable` (driver path)

### Verification

Write 0 → getevent on event1 shows nothing (no interrupt → no events).
Write 1 → restore.
Note: reading irq_enable always returns `1` regardless of write value — write and read have separate semantics.

## Other accessible sysfs nodes

- `double_tap_enable` (rw) — double-tap-to-wake
- `capacitive_keys_enable` (rw) — capacitive buttons
- `wake_gesture` (rw) — wake gestures
- `reset` (wo) — reset controller
- `suspend` (wo) — suspend controller
- `power/control` — "auto" (can set "on" or "off")
- `0dbutton` — 0D button setting
- `buildid`, `productinfo`, `flashprog`, `rmidev` — diagnostic entries
