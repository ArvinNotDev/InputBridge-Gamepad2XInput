# InputBridge-Gamepad2XInput v2.0.8

Release date: **September 26, 2026**

This release adds per-controller Sony DualSense Lightbar control while keeping
the existing input mapping, XInput emulation, vibration, gyro, touchpad,
profiles, and HidHide behavior unchanged.

## Highlights

- Custom Lightbar color for every DualSense controller independently.
- Persistent Lightbar settings across application restarts and reconnects when
  Windows exposes a stable controller identity.
- Optional battery-level Lightbar mode.
- Optional charging indication.
- DualSense USB and Bluetooth Lightbar report construction.
- DualSense Edge support (`VID 0x054C`, `PID 0x0DF2`).
- Shared Bluetooth output sequencing between Lightbar and rumble reports.
- Version bump from `2.0.7` to `2.0.8`.

## How to use it

1. Start InputBridge-Gamepad2XInput and open **Controller Emulation**.
2. Add a DualSense or DualSense Edge controller.
3. Click the controller's **Lightbar** button.
4. Configure:
   - **Lightbar On**
   - Custom RGB color
   - HEX color preview/value
   - **Battery Lightbar**
   - **Charging indication**
5. Click **Save**.

The dialog identifies the controller being edited. Each controller has a
separate saved color and Lightbar state, so changing Controller A does not
change Controller B.

## Battery Lightbar behavior

Battery mode is temporary visualization. It never overwrites the saved custom
color.

| Battery level | Color |
| --- | --- |
| 70–100% | Green |
| 40–69% | Yellow |
| 20–39% | Orange |
| 0–19% | Red |

When charging indication is enabled, charging uses a subtle cyan status color.
After charging stops, the Lightbar returns to the battery color when battery
mode is enabled, or the saved custom color when it is disabled.

The application reuses the existing DualSense battery parsing path. The
transport-specific report offset is handled separately for Bluetooth and USB.

## Controller identity and persistence

Settings are stored in the existing `config/settings.conf` file. The identity
used for Lightbar preferences is selected in this order:

1. HID serial number.
2. Bluetooth address found in the HID path.
3. HID path as a fallback.

This keeps preferences associated with the physical controller when its live
connection path changes after reconnecting. If a device exposes no stable
serial number or address, the fallback path may change when Windows creates a
new HID interface.

## DualSense output protocol

The implementation uses DualSense reports only. It does not use DualShock 4
output report formats (`0x05` or `0x11`).

### USB

- HIDAPI buffer length: 63 bytes.
- Report ID: `0x02`.
- Lightbar valid flag: `report[2] = 0x04`.
- Lightbar on/setup fields: `report[39] = 0x02`, `report[42] = 0x01`.
- RGB bytes: `report[45]`, `report[46]`, `report[47]`.
- No CRC.

### Bluetooth

- HIDAPI buffer length: 78 bytes.
- Report ID: `0x31`.
- Sequence: high nibble of `report[1]`, wrapping `0..15`.
- Tag: `report[2] = 0x10`.
- Lightbar valid flag: `report[4] = 0x04`.
- Lightbar on/setup fields: `report[41] = 0x02`, `report[44] = 0x01`.
- RGB bytes: `report[47]`, `report[48]`, `report[49]`.
- CRC: little-endian bytes `report[74:78]`.

The Bluetooth CRC is calculated as:

```python
crc_input = bytes([0xA2]) + bytes(report[:-4])
crc = binascii.crc32(crc_input) & 0xFFFFFFFF
report[74:78] = crc.to_bytes(4, "little")
```

The `0xA2` seed participates in the CRC calculation but is not prepended to
the HIDAPI buffer passed to `hid_write()`.

## Performance and output safety

- Identical Lightbar states are not resent continuously.
- Updates are queued and coalesced so the latest requested color wins.
- Lightbar and rumble output writes are serialized per controller.
- Bluetooth sequence state is shared per controller, preventing Lightbar and
  rumble reports from using conflicting sequence values.
- `led_brightness` is not interpreted as Lightbar RGB brightness. RGB scaling
  remains a software responsibility if a brightness control is added later.

## Compatibility

- Windows 10 or later, x64.
- Existing ViGEmBus requirement remains unchanged for virtual Xbox/XInput
  emulation.
- Bluetooth DualSense use is supported and was the available hardware path
  during release validation.
- USB report construction is included and covered by automated checks. A USB
  hardware run requires a controller connected by cable.
- Existing DualShock 4, generic HID, profiles, hotkeys, mouse mode, vibration,
  HidHide, and remote gamepad functionality remain available.

## Validation

Focused validation for this release includes:

- USB report ID, length, flags, Lightbar on fields, and RGB offsets.
- Bluetooth report ID, length, sequence nibble, flags, RGB offsets, and CRC.
- Per-controller Bluetooth sequence allocation and wraparound.
- Duplicate output suppression and latest-state coalescing.
- Independent save/load of two controllers' settings.
- Battery color transitions and restoration of the saved custom color.
- DualSense battery status parsing and USB/Bluetooth input offsets.
- Stable controller identity selection.
- Offscreen Lightbar dialog construction.
- Python compilation and application import.

The focused test set passes on the release source tree. The executable is not
included in this repository commit; build and upload the Windows `.exe` as the
release asset.

## Suggested GitHub release assets

Upload the executable built from this tag/commit:

```text
InputBridge-Gamepad2XInput.exe
```

If you distribute an onedir build, upload the packaged directory or archive
using the existing PyInstaller specification. Include the SHA-256 checksum in
the GitHub release description if you publish an archive alongside the
one-file executable.
