# Qin 2 (多亲2): Magisk Upgrade on Locked Bootloader (arm32)

## Device Profile

- Model: SM1908012103 (DuoQin/Qin 2)
- CPU: Spreadtrum SC9832E (4x A53, arm32/armv7l)
- RAM: 878MB total (~477MB available)
- Android: 9 Go (SDK 28)
- Bootloader: Locked (BL lock死), no unlock method available
- ADB: USB only (no `adb root` in production builds)
- Magisk (old): v20.4 (20400) — from ~2020
- Magisk Manager (old): v7.5.1
- Network: SSH on port 8022 via Termux

## Upgrade Path

The locked bootloader prevents boot image patching (the normal Magisk install flow). However, since Magisk v20.4 is already installed, you can:

1. **Update the Magisk Manager (the APK)** — this replaces the Manager app
2. **Use the new Manager's in-app Magisk binary upgrade** — or download the latest APK

### Step 1: Download and Install New Magisk Manager APK

```bash
# Determine version cap: arm32 support ended at Magisk v25.2 (later versions are arm64-only)
# Install via ADB
curl -sL -o /tmp/magisk-v25.2.apk \
  "https://github.com/topjohnwu/Magisk/releases/download/v25.2/Magisk-v25.2.apk"
adb -s <SERIAL> install /tmp/magisk-v25.2.apk
```

Note: As of mid-2026, the latest Manager is v30.6/v30.7. After installing v25.2, the Manager will self-update to the latest via its in-app "更新" (Update) button. The app version and Magisk binary version are separate — the Manager can be v30.6 while the installed binary is still v20.4.

### Step 2: Open the New Manager

```bash
adb -s <SERIAL> shell am start -n com.topjohnwu.magisk/.ui.MainActivity
sleep 3
```

### Step 3: Dismiss the "不支持的 Magisk 版本" Dialog

The new Manager (v25.2+) detects the old binary (v20.4) and shows:

```
Title: "不支持的 Magisk 版本"
Body: "应用不支持低于 v22.0 版本的 Magisk，表现为未安装状态。但升级功能可用，请尽快在应用内升级 Magisk。"
Button: "确定" (OK)
```

Tap "确定" (OK) to dismiss. On a 576x1440 display, the button is approximately centered at x=288, y=850.

### Step 4: Tap "更新"/"安装" in Magisk Section

After dismissing the dialog, the home screen shows the Magisk card with a blue "更新" (Update) or "安装" (Install) button. Tap it.

This triggers the "需要修复运行环境" (Runtime environment needs repair) dialog:

```
Title: "需要修复运行环境"
Body: "需要重新安装才能使 Magisk 正常工作。请在应用内重新安装，recovery 模式无法正确获取设备信息。"
Buttons: "取消" (Cancel) / "确定" (Confirm)
```

Tap "确定" (Confirm) at approximately x=430, y=650. This should trigger Magisk to download the new binary and start the upgrade, which may request su authorization from v20.4.

### Step 5: Su Authorization (Key Blocking Point)

The su request appears as `com.topjohnwu.magisk/.ui.surequest.SuRequestActivity` in `dumpsys window windows | grep mCurrentFocus`. Check for it after tapping "确定":

```bash
# After tapping, immediately check:
adb shell dumpsys window windows | grep mCurrentFocus
# Expected: ...surequest.SuRequestActivity
```

If the dialog appears, tap "Grant" (授予/允许). If it doesn't appear, su was never triggered — the new Manager may be trying to download files and install silently, which fails without root on locked bootloader (the binary needs to patch init, which requires root).

### Known Outcome

On this arm32 locked-bootloader device:
- Magisk Manager can be upgraded from v7.5.1 to the latest (v30.6+)
- The Manager APK itself doesn't need root to update (standard Package Installer)
- However, upgrading the Magisk *binary* (daemon) from v20.4 → v22+ requires su/root, which on old Magisk v20.4 means a GUI authorization dialog on the phone screen
- The su authorization is the blocking point: if nobody taps "Grant" on the phone, the upgrade halts
- Without root from su, the "Magisk" card shows: "当前 无法获取", "Zygisk 否", "Ramdisk 否"
- The device remains functional with the new Manager app but old Magisk binary

## CRITICAL PITFALL: "确定" on "需要修复运行环境" → Boot Loop on Locked Bootloader

Tapping "确定" (Confirm) on the "需要修复运行环境" (Runtime environment needs repair) dialog **causes a boot loop on locked-bootloader devices**. The phone reboots, gets stuck at boot animation, and cannot boot into the system.

### Root Cause

The new Magisk Manager (v25.2+) detects the old binary (v20.4) as incompatible and offers to "repair" the runtime environment. On a device with a **locked bootloader**, the repair process involves:

1. Attempting to patch/replace the boot image with a new Magisk init
2. Rebooting to activate the changes
3. The boot image write either fails partially or produces an incompatible image
4. The kernel panics during boot, resulting in an infinite boot loop

The Manager's warning text explicitly says "请在应用内重新安装，recovery 模式无法正确获取设备信息" (please reinstall within the app; recovery mode cannot correctly obtain device information) — but the in-app reinstall fails on locked bootloaders, and recovery mode is the only escape.

### Recovery: Booting to Recovery Mode on Spreadtrum SC9832E

When the phone is stuck at boot animation:

1. **Force shutdown**: Hold Power button for 15+ seconds until the screen goes black and phone stops vibrating
2. **Boot to recovery**: From a fully-off state, simultaneously press and hold **Power + Volume Down**
3. Keep holding both buttons until the recovery menu appears (may take 5-10 seconds)
4. If Power+Volume Down doesn't work, try **Power + Volume Up** (some Spreadtrum variants)
5. In recovery, use Volume keys to navigate, Power to select

### Recovery Options (in order of safety)

1. **Wipe cache partition** — safest, preserves all data. May resolve boot loop if the issue is only cache corruption.
2. **Factory reset / Wipe data** — erases all user data. Usually fixes boot loops from failed system modifications.
3. **Power off** — select "Power off" from recovery menu, then try normal boot. Sometimes a cold boot after forced shutdown is enough.

If even recovery doesn't load, the device may need flashing via SP Flash Tool (Spreadtrum's proprietary flashing tool), which requires the stock ROM scatter file and a Windows host.

### Safe Alternative: Do NOT Tap "确定"

Instead of tapping "确定" on the "需要修复运行环境" dialog:

- Accept that the Magisk *binary* cannot be upgraded on a locked bootloader
- The new Manager app (v30.6+) can still be used for non-root features (module management, logs, settings)
- su authorization from the old v20.4 binary will work once granted (if V20.4's su/bin is properly configured)
- The "当前 无法获取" status is cosmetic — the old Magisk binary still runs its su daemon in the background
- To actually upgrade Magisk on a locked bootloader: the phone must be unlocked via an official unlock method (if one exists for the device) or via exploits (none known for SC9832E)

## Package Installer Dialog: Magisk Manager APK Update

When the Manager self-updates (e.g., v25.2 → v30.6 via the "更新" button in the App section), Android's **system Package Installer** shows:

```
Title: "Magisk"
Body: "是否要为这一现有应用安装更新？您现有的数据不会丢失，且安装过程无需任何特殊权限。"
Buttons: "取消" (Cancel) / "安装" (Install)
```

On a 576x1440 display, tap coordinates for "安装" (Install) are approximately:
- **x=510, y=1400** (bottom-right area)
- The button is near the bottom edge of the screen, right-aligned
- "取消" is at approximately x=300, y=1400

The update goes through without requiring root — standard APK update via PackageInstallerActivity.

## Key Screenshots Analysis

- 576x1440 PNG captures from `screencap -p`
- When screen is off: 6KB black PNG (same pixel data repeated)
- When screen is on: typically 500KB-1.5MB depending on UI complexity
- Use `vision_analyze` to read Chinese UI dialogs and estimate button coordinates
- Multiple capture rounds needed as dialog state changes

## Hard Brick Diagnosis: PMIC Power Loop vs Soft Brick

When "确定" is tapped on the "需要修复运行环境" dialog and the phone enters a boot loop, the severity depends on whether recovery mode is accessible:

### Soft Brick (Recovery Accessible)
- Power button can fully shut down the phone
- Recovery mode (Power+Volume Down/Up) works
- `adb devices` may detect the phone during boot
- Fix: Wipe cache or factory reset in recovery, then reflash stock firmware

### Hard Brick — PMIC Power Loop (Recovery Inaccessible)
**This is the more severe case**, observed on Qin 2 (Spreadtrum SC9832E):
- **Power button cannot force shutdown** — screen goes black for 2-3 seconds, then immediately returns to boot animation. The PMIC (Power Management IC) is locked in a restart cycle.
- Recovery mode (Power+Volume Up/Down) — no response from any combination
- ADB/Fastboot — device not enumerated on USB at all
- SSH — unreachable (Termux SSHd not running)
- **Root cause**: The boot partition damage causes the kernel to panic before the PMIC receives any shutdown signal. The PMIC's watchdog timer triggers a warm reset, creating an infinite loop.
- **EDL/Download mode cannot be entered** via software when the device is in this state — the USB controller never initializes

### How to Confirm PMIC Power Loop
1. Press and hold Power button for 15-20 seconds
2. Screen goes black briefly (2-3s), then returns to boot animation without user interaction
3. No amount of power-button holding changes this behavior
4. USB shows no new devices in `system_profiler SPUSBDataType` or `adb devices`
5. The phone feels warm to the touch — PMIC is continuously delivering power

The ONLY reliable way to break this cycle is to **physically disconnect the battery**.

## Hard Brick Recovery: ResearchDownload (Spreadtrum EDL)

When recovery mode and ADB are both inaccessible, the Spreadtrum SC9832E chipset has a BootROM-level download mode called **ResearchDownload** (equivalent to Qualcomm's EDL 9008 mode). This mode operates before the bootloader and is immune to bootloader lock status.

### Prerequisites

1. **Power off the phone fully** — must physically disconnect the battery (power button is insufficient in PMIC loop)
2. **ResearchDownload mode entry** — two methods:

#### Method A: Software Trigger (try first)
- With the phone fully powered off (battery disconnected and reconnected)
- Do NOT plug in USB yet
- Simultaneously hold **Volume Up + Volume Down** (both together)
- While holding both volume buttons, plug USB into the phone
- On Windows PC, device manager should show "Spreadtrum USB Download Device" or "SPRD U2S Diag"
- On macOS, `system_profiler SPUSBDataType` should show a vendor with Spreadtrum VID (0x1782)

#### Method B: Hardware Test Point (when software method fails)
On Qin 2 (and many Spreadtrum SC9832E devices), the software trigger may not work — the USB controller requires a hardware signal to enter download mode. Required:
- Open the phone case
- Locate the **BootROM test points** on the motherboard — typically two bare metal contacts near the USB connector or the SoC
- Short these contacts (tweezers or wire) while plugging in USB
- Search terms for finding test point locations: "多亲Qin2 短接点", "SC9832E test point", "Spreadtrum SC9832E download mode test point"
- XDA thread https://xdaforums.com/t/xiaomi-qin-2-ai-rom-help.4008237/ and Hovatek forum may have photos

### Tools Needed

#### SPD ResearchDownload Tool (Windows)
- Tool name: SPD Research Tool (also called ResearchDownload or SPD Flash Tool)
- Version: R27.24.2301 (latest, 13MB, portable — no install needed)
- Download: `https://spdflashtool.com/wp-content/uploads/SPD_Research_Tool_R27.24.2301.zip`
- Alternative mirrors: androidfilehost.com, androidmtk.com
- macOS workaround: Install Wine via `brew install --cask wine-stable`, then run `ResearchDownload.exe`
- The tool is officially called "SPD" (Spreadtrum) — not SP Flash Tool (MediaTek)

#### SPD USB Driver (Windows)
- Download: `https://spreadtrumdriver.com/`
- Required for Windows to recognize the device in download mode

#### PAC Firmware (Stock ROM)
- **Format**: `.pac` (Spreadtrum firmware package format), NOT `.zip` or `.img`
- Size: typically 1-2GB
- Contains: bootloader, boot image, system, vendor, modem, NV items, etc.
- **Sourcing**: Difficult for the Qin 2 (SM1908012103). Low device popularity means few pre-built PAC files exist online.
- **Search terms**: "多亲Qin2 SM1908012103 PAC", "Qin2 SC9832E 线刷包", "Qin 2 stock firmware pac"
- **Known sources**:
  - 66rom.com https://www.66rom.com/thread-19165-1-1.html (may have Qin 2 Pro PAC)
  - XDA: https://xdaforums.com/t/xiaomi-qin-2-ai-rom-help.4008237/
  - Hovatek: https://www.hovatek.com/forum/thread-31241.html
  - FOTA firmware link (may be dead): https://yadi.sk/d/K0EFeekyddtQ7w
- **Pro vs Regular**: The Qin 2 Pro has 2GB RAM and different screen resolution. PAC files may NOT be interchangeable. Always match exact model SM1908012103.
- **CM2 Dongle**: If no PAC file is available online, a CM2 hardware dongle with CM2SP2 module can create a PAC file from a known-working device. This requires a functional phone to dump from — not helpful for brick recovery.

### Flashing Procedure (once in download mode)

1. Open ResearchDownload.exe (portable, no install)
2. Click "Load Firmware" / first button → select the .pac file
3. Wait for the tool to parse the PAC (loads partition layout)
4. Default settings should work — do NOT change LCD/Preloader options unless you know what you're doing
5. Ensure phone is connected and recognized (status bar shows "Connected")
6. Click "Start" (or "Download") to begin flashing
7. Progress bar advances as partitions are written (bootloader, boot, system, etc.)
8. When finished: "PASS" or green checkmark
9. Disconnect USB, do NOT press any button — wait 10 seconds for the phone to auto-reboot
10. First boot after PAC flash takes 3-5 minutes (factory reset happens automatically)

### Flashing Precautions
- **USB cable**: Use the original cable or a known-good data cable (not charge-only)
- **Interruption**: Do NOT unplug during flashing. A partial flash bricks the device harder.
- **Wrong PAC**: Flashing the wrong model's PAC may brick the LCD or modem. Check double.
- **Data loss**: Full PAC flash wipes EVERYTHING — no data survives.
- **After flash**: The phone boots as factory-fresh (Android 9 Go). All apps, settings, and Magisk are gone. ADB on first boot shows "unauthorized" until you accept the RSA dialog on screen.
- **Magisk recovery**: After stock boot, reinstall Magisk is possible only if the bootloader was somehow unlocked — which is separate challenge (see discussion below).

### Boot Mode vs Download Mode on Spreadtrum

| Mode | Enter Method | USB Enumeration | Use Case |
|------|-------------|-----------------|----------|
| **Normal boot** | Power button | ADB device (if debug on) | Daily use |
| **Recovery** | Power+Vol Down/Up | ADB in recovery | Cache wipe, factory reset |
| **Fastboot** | Not available on SC9832E | — | — |
| **ResearchDownload (EDL)** | Hardware test point or Vol Up+Down+USB | "SPRD U2S" or "Spreadtrum USB Download" | Full firmware flash |
| **Meta mode** | ResearchDownload tool option | Same as download | NV items, RF calibration |

### Practical Recovery Summary (Qin 2 SM1908012103)

The actual recovery path from a PMIC-loop hard brick:

1. **Drain the battery completely** — leave the phone untouched for 1-2 days until the screen is black and no amount of button pressing triggers the boot animation. This is the only safe way to break the PMIC loop without opening the phone.
2. **Immediately upon battery depletion** → plug USB while holding Volume Up+Down → try software EDL trigger
3. **If software EDL fails** (likely on Qin 2) → disconnect battery (open case, find battery connector on motherboard right side, gently pry off)
4. **Reconnect battery** → try software EDL again
5. **If still fails** → find motherboard test points on SC9832E, short while plugging USB
6. **Once in download mode** → ResearchDownload tool + PAC firmware → flash
7. **If no PAC file exists** → device is unrecoverable without buying a CM2 dongle or finding someone willing to dump their working phone's firmware

## Related

- Main skill section: ADB Screen Automation (Headless UI Interaction) in SKILL.md
- ADB Screen Automation subsection: Screen State Diagnostics, Dialog Navigation Guidelines, Su Authorization on Locked-Bootloader + Old Magisk, Pixel Coordinate Estimation
- `references/arm32-armv7l-limitations.md` — architectural constraints for this device class
- SKILL.md Pitfall #23 — warning about tapping "确定" on "需要修复运行环境" on locked bootloader
