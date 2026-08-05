# ESP32 Web Flasher

You can try it out youself on Github pages (as an example I used EmbeddedScreenSharing). [Wizard](https://lemio.github.io/EmbeddedScreenSharing/wizard.html) & [Single Page](https://lemio.github.io/EmbeddedScreenSharing/index.html)

https://github.com/user-attachments/assets/0cbbe652-9fc3-4732-ac1d-91ecdca1defe

A simple, browser-based tool for flashing ESP32 devices (plain ESP32, S2, S3, C3, C6, ...) using the Web Serial API. Built with the ESPtool-js library made by [Esperessif](https://github.com/espressif/esptool-js), which auto-detects whichever chip in the family is actually connected. Next to flashing it can also alter the firmware by replacing *magic* keywords with other content; this could be usefull for wifi setup or other settings that you want end-users to change.

**This is a generic tool, not tied to any one project** - no firmware ships with this
repo. Point it at your own project's `manifest.json` (any PlatformIO-based repo can
generate one automatically, no manual `config.js` editing) or add entries to `config.js`
by hand. See [For PlatformIO projects: automate it with the reusable Action](#for-platformio-projects-automate-it-with-the-reusable-action)
for the fastest path if you're already using PlatformIO - a real example:
[esp32_PoweredUp](https://github.com/lemio/esp32_PoweredUp), whose own GitHub Pages site
is built entirely by this tool's reusable Action.

<img width="3432" height="2418" alt="image" src="https://github.com/user-attachments/assets/624c3a63-f4a3-4385-8ca7-27c81ae52997" />
This webflasher has the potential to help library builders to get users to quickly test the examples in the library.

## The User Interface

This project contains two different types of interface one is the index.html the other is wizard.html. wizard.html is intended for beginners and people that normally don't deal with terminals, firmware etc. You can replace the short videos with your own product.

The index.html flow is intended for more experienced users; and also gives you some debugging information.

## Features

- 🌐 **Browser-based**: No need to install drivers or tools
- 🚀 **Easy to use**: Simple process to flash your device
- 📱 **Multiple firmware support**: Select from available firmware options
- 🔧 **Dynamic configuration**: Replace WiFi SSID, password, and mDNS hostname before flashing or any other variable you might define.
- 💾 **Persistent settings**: Configuration values saved in browser localStorage
- 🔒 **Firmware integrity**: Automatic checksum and SHA256 recalculation
- 📊 **Real-time progress**: Visual feedback during the flashing process
- 🔐 **Secure**: All processing happens locally in your browser
- 🖥️ **Built-in serial monitor**: Starts automatically once flashing finishes, showing
  whatever your firmware prints to `Serial` - no separate tool needed, especially useful
  for beginners confirming their firmware is actually doing what they expect
- 🎨 **Rebrandable**: a `manifest.json`'s `site` block renames the tool and swaps its
  instructional videos for ones specific to your project - no forking required

## Requirements

- A modern browser with Web Serial API support:
  - Google Chrome (version 89+)
  - Microsoft Edge (version 89+)
  - Opera (version 75+)
- An ESP32-family device (plain ESP32, S2, S3, C3, C6, ...) connected via USB whose
  USB-to-serial bridge chip's vendor ID is listed in `config.js`'s `FILTERS` (see
  "Configuration File Structure" below - CH340, CP210x, FTDI and native USB-JTAG/CDC are
  covered by default). Only needs to be in download mode once you click Flash Device -
  connecting doesn't touch its boot state.

## Usage

1. **Open the flasher**: Open `index.html` in a supported browser
2. **Select firmware**: Choose the firmware you want to flash from the dropdown
3. **Configure variables** (if available): Enter your WiFi SSID, password, and mDNS hostname
4. **Connect device**: Click "Connect to ESP32" (label follows `config.js`'s `CHIP_NAME`) and select your device from the browser popup
5. **Flash**: Click "Flash Device" to start the flashing process

## Available Firmware

None built in - `config.js`'s `FIRMWARE_CONFIGS` starts empty. Either point this tool at
a `manifest.json` your own project generates (see
[For PlatformIO projects](#for-platformio-projects-automate-it-with-the-reusable-action)
below), or add entries to `config.js` directly (see
[Adding Your Own Firmware](#adding-your-own-firmware-manual--non-platformio-projects)).

## How It Works

This tool uses:
- [esptool](https://github.com/espressif/esptool-js) -  JavaScript implementation of esptool
- Web Serial API - For communicating with the ESP32 over USB
- Web Crypto API - For SHA256 hash recalculation

### Variable Replacement

For firmware with configurable variables:
1. Variables are marked with special delimiters (e.g., `|*S*|` for SSID) in 100-byte padded regions
2. When you enter values, they replace the entire 100-byte region
3. The firmware checksum is automatically recalculated over segment data only (see [CHECKSUM_ALGORITHM.md](CHECKSUM_ALGORITHM.md))
4. If present, the SHA256 digest is recalculated and appended

<img width="8428" height="2926" alt="image" src="https://github.com/user-attachments/assets/1edfbe3e-7257-45a0-90f9-35487db0d376" />


### Flashing Process

The firmware is loaded from the repository and flashed to the following addresses:
- `0x0000`: bootloader.bin
- `0x8000`: partitions.bin
- `0xe000`: boot_app0.bin
- `0x10000`: firmware.bin (with variable replacements if configured)

## Configure it for your own project

All firmware configurations and device settings are now centralized in `config.js`, making it easy to add your own firmware or devices.

### Configuration File Structure

The `config.js` file contains two main objects:

#### 1. **CONFIG** - General device settings

```javascript
const CONFIG = {
    DISCONNECT_WAIT_MS: 1500,      // Wait time after disconnect
    BAUD_RATE: 460800,              // Serial speed for the whole session (sync + flashing).
                                     // Higher isn't automatically riskier - the ROM auto-detects
                                     // baud from the sync command itself, and 115200 has been
                                     // observed to be *less* reliable than 460800 on some CH340
                                     // boards (garbled sync/flash reads). If flashing is unreliable
                                     // on your hardware, try both a higher and a lower value.
    CHIP_NAME: "ESP32",             // Cosmetic label only (button text, boot-mode instructions,
                                     // the downloaded esptool.py comment) - esptool-js auto-detects
                                     // the real connected chip regardless, so this doesn't restrict
                                     // which ESP32-family chip can connect. Set to whatever your
                                     // project targets, e.g. "ESP32-S3" or "ESP32-C3".
    FILTERS: [                      // Which USB-to-serial bridge vendor IDs show up in the
                                     // browser's connect picker - a device not covered here isn't
                                     // selectable
        {usbVendorId: 0x1A86},      // WCH (CH340/CH343/CH9102) - most common on generic/plain ESP32 boards
        {usbVendorId: 0x10C4},      // SILICON_LABS (CP210x)
        {usbVendorId: 0x303A},      // ESPRESSIF (native USB-JTAG/CDC)
        {usbVendorId: 0x0403},      // FTDI
        {usbVendorId: 0x1B4F},      // SparkFun
        {usbVendorId: 0x2341}       // Arduino
    ]
};
```

**Adding a new USB vendor:**
If your device isn't detected, find its vendor ID using the browser console:
```javascript
navigator.serial.requestPort().then(x => console.log(x.getInfo()))
```
Then add it to the `FILTERS` array. A consuming repo that generates `manifest.json` via the
reusable Action can instead set `site.filters`/`site.chipName` in `flasher-manifest.yml` - see
"Site-wide branding" below - without touching `config.js` at all.

#### 2. **FIRMWARE_CONFIGS** - Firmware definitions

Each firmware configuration has the following structure:

```javascript
'firmware-key': {
    name: 'Human-readable name',
    description: 'Brief description (wizard only)',
    hardware: 'ESP32-S3-DevKitC-1',  // Board/chip this targets - shown in the UI so users know what to flash it to
    expectedBehavior: [              // Optional (wizard only) - array of expected behaviors, shown as a
        'What happens after flashing', // bulleted list in step 4. Falls back to a single item built from
        'Can include HTML like <b>bold</b> or <a href="...">links</a>' // `description` above if omitted.
    ],
    files: [                         // Firmware files to flash
        { path: 'path/to/bootloader.bin', offset: 0x0000 },
        { path: 'path/to/partitions.bin', offset: 0x8000 },
        { path: 'path/to/boot_app0.bin',  offset: 0xe000 },
        { path: 'path/to/firmware.bin',   offset: 0x10000 }
    ],
    variables: [                     // Optional: configurable variables
        {
            firmware_name: '|*S*|',           // Placeholder in firmware
            readable_name: 'WiFi Name',       // Label shown to user
            default_value: 'MyNetwork',       // Default value
            max_length: 100,                  // Max bytes (with null padding)
            postfix: '.local'                 // Optional: append to display
        },
        {
            firmware_name: '|*ROTATION*|',    // Same placeholder/patching mechanism as above, but
            readable_name: 'Screen Rotation', // rendered as a <select> dropdown instead of free text
            type: 'enum',                     // by setting type: 'enum' and providing `options`
            options: [                        // `value` is written into the firmware, `label` is
                { value: '0', label: '0°' },    // shown to the user. A plain string entry (no
                { value: '1', label: '90°' },   // {value, label}) is used as both.
                { value: '2', label: '180°' },
                { value: '3', label: '270°' }
            ],
            default_value: '1',
            max_length: 16                     // still needs to fit firmware_name itself
        },
        {
            firmware_name: '|*TZ*|',          // type: 'timezone' renders a <select> populated from
            readable_name: 'Timezone',        // every IANA zone via the browser's own
            type: 'timezone',                 // Intl.supportedValuesOf('timeZone') - no options list
            max_length: 64                    // needed. Defaults to the browser's own detected zone
        }                                     // (Intl.DateTimeFormat().resolvedOptions().timeZone)
    ],                                        // unless localStorage already has a prior choice. What
                                               // gets patched into firmware isn't the IANA name though
                                               // - it's looked up in posix_tz_db.js and the matching
                                               // POSIX TZ string (e.g. "EST5EDT,M3.2.0,M11.1.0") is
                                               // written instead, since that's what a configTzTime()
                                               // -style firmware API actually needs.
    resetVideo: 'https://.../my-reset-instructions.webm', // Optional (wizard.html only): overrides the
                                                             // step-3 "press RESET" video for this firmware
    sourceUrl: 'https://github.com/you/your-repo/tree/main/examples/foo' // Optional: "View source"
                                                                           // link on the firmware card/info panel
}
```

This will result in this UI:
<img width="481" height="208" alt="image" src="https://github.com/user-attachments/assets/8c104666-036a-4e3f-b586-23093ea244ac" />

#### 3. Site-wide branding (manifest.json only)

Firmware entries aren't the only thing a `manifest.json` (see "For PlatformIO projects"
below) can carry - a `site` block alongside them renames the tool itself and swaps its
generic instructional media for something specific to your project:

```javascript
{
  "site": {
    "title": "My Project Flasher",       // replaces the page <title> and <h1> in both index.html and wizard.html
    "subtitle": "Flash any example straight from your browser", // shown under the <h1>
    "bootModeVideo": "https://.../my-boot-instructions.webm",   // wizard.html step 1 only - see note below
    "chipName": "ESP32-C3",              // overrides config.js's CHIP_NAME - drives the connect button/boot-mode
                                          // instructions text and the chip flag in the downloaded esptool.py comment
    "filters": [                         // overrides config.js's FILTERS - which USB devices show up in the
      { "usbVendorId": 6790 }            // browser's connect picker (6790 = 0x1A86, WCH/CH340)
    ]
  },
  "firmwares": { ... }
}
```

`chipName` and `filters` are cosmetic-and-picker only, same as `config.js`'s `CHIP_NAME`/`FILTERS`
(see "Configuration File Structure" below) - they don't restrict which chip can actually
connect, since esptool-js auto-detects the real chip on sync regardless. They just mean a
consuming repo targeting a plain ESP32 (or C3/C6/etc.) doesn't need to fork `config.js` by
hand to get accurate button text and the right devices listed in the picker.

`bootModeVideo` is site-wide only, not per-firmware: wizard.html's step 1 (where it's
shown) runs *before* firmware selection in step 2, so there's no firmware-specific video
to pick yet. `resetVideo` (step 3, shown *after* selection) can be set per-firmware
instead - see the `FIRMWARE_CONFIGS` structure above - and falls back to `site.resetVideo`
if the selected firmware doesn't set its own.

This has no equivalent in hand-written `config.js` entries - it's specifically a
`manifest.json`-level concept, generated from your own repo's `flasher-manifest.yml`
(see "For PlatformIO projects" below) via a top-level `site:` key alongside the
per-example `examples:` key.

### For PlatformIO projects: automate it with the reusable Action

Everything below this section - manually locating `boot_app0.bin`, copying files into a
subdirectory, hand-writing a `config.js` entry - is exactly what
[`action/`](action/action.yml) automates for any PlatformIO-based repo. Instead of
maintaining firmware here by hand, your own repo can:

1. Have a `platformio.ini` that builds one environment per firmware/example you want
   flashable (see [esp32_PoweredUp](https://github.com/lemio/esp32_PoweredUp)'s root
   `platformio.ini` for a working example - one environment per example sketch).
2. Add a `flasher-manifest.yml` declaring each environment's display name, description,
   any flash-time-patchable variables (the WiFi SSID/password pattern above,
   generalized), and optionally a top-level `site:` block to rename the tool and swap
   its instructional videos for ones specific to your project (see "Site-wide branding"
   above).
3. Call this Action from your own repo's workflow:
   ```yaml
   - uses: lemio/ESP32-S3-Flasher/action@main
     with:
       output-dir: docs   # or wherever your repo publishes GitHub Pages from
   ```
   This runs `pio run`, collects every environment's `bootloader.bin`/`partitions.bin`/
   `firmware.bin` (plus a bundled `boot_app0.bin` - no more hunting for it in
   `~/.platformio/packages/...`), and writes it all out alongside a `manifest.json` and
   a copy of this repo's flashing UI (`index.html`, `wizard.html`, `config.js`) - a
   complete, ready-to-publish GitHub Pages folder.
4. Commit and push that output folder to your own repo (same-repo, default
   `GITHUB_TOKEN`, no secrets needed) and enable GitHub Pages on it.

The web app here (`index.html`/`wizard.html`) automatically `fetch()`es a
`manifest.json` next to itself on page load - shape `{site: {...}, firmwares: {...}}` -
merging `firmwares` into `FIRMWARE_CONFIGS` alongside whatever's hardcoded in
`config.js`, and applying `site`'s branding overrides if present. So a repo using the
Action gets its own fully independent flasher page, with its own firmware list and its
own name, without touching this repo's `config.js` or HTML at all.

### Adding Your Own Firmware (manual / non-PlatformIO projects)

1. **Prepare your firmware files:**

https://github.com/user-attachments/assets/97ec71ab-b551-4dcd-8168-1653a513b4b9

   - Place them in a subdirectory (e.g., `MyDevice/Firmware/`)
   - You'll need: `bootloader.bin`, `partitions.bin`, `boot_app0.bin`, `firmware.bin`
   - You can find them in the subfolder of platformIO project; for example `LilyGo-AMOLED-WebJPEG/.pio/build/T-Display-AMOLED/firmware.bin` 
   - Only the `boot_app0.bin` you can find in `~/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin` on mac
   - To find these files you can use the *Verbose Upload* option in platformIO

3. **Add configuration to `config.js`:**

```javascript
'my-custom-firmware': {
    name: 'My Custom Device Firmware',
    description: 'Custom firmware for my ESP32-S3 project',
    expectedBehavior: [
        'Device will connect to configured WiFi',
        'Access at http://mydevice.local'
    ],
    files: [
        { path: 'MyDevice/Firmware/bootloader.bin', offset: 0x0000 },
        { path: 'MyDevice/Firmware/partitions.bin', offset: 0x8000 },
        { path: 'MyDevice/Firmware/boot_app0.bin',  offset: 0xe000 },
        { path: 'MyDevice/Firmware/firmware.bin',   offset: 0x10000 }
    ]
}
```

3. **Add variables (optional):**

If your firmware supports dynamic configuration, embed placeholders in your firmware code:

```cpp
// In your ESP32 code:
const char WIFI_SSID[100] = "|*SSID*|";
const char WIFI_PASS[100] = "|*PASS*|";
```

Then configure them in `config.js`:

```javascript
variables: [
    {
        firmware_name: '|*SSID*|',
        readable_name: 'WiFi Network Name',
        default_value: 'MyWiFi',
        max_length: 100
    },
    {
        firmware_name: '|*PASS*|',
        readable_name: 'WiFi Password',
        default_value: 'password123',
        max_length: 100
    },
    {
        // Constrained to a fixed set of choices - rendered as a dropdown instead of
        // a text field. `value` is what's written into the firmware; `label` is
        // what the user sees. Useful for things like tft.setRotation(N) where only
        // a handful of values are ever valid.
        firmware_name: '|*ROTATION*|',
        readable_name: 'Screen Rotation',
        type: 'enum',
        options: [
            { value: '0', label: '0°' },
            { value: '1', label: '90°' },
            { value: '2', label: '180°' },
            { value: '3', label: '270°' }
        ],
        default_value: '1',
        max_length: 16
    },
    {
        // Lets the user pick their timezone from every IANA zone the browser knows
        // about (via Intl.supportedValuesOf('timeZone')), auto-selecting the
        // browser's own detected zone (Intl.DateTimeFormat().resolvedOptions().timeZone)
        // as the default. What's actually written into firmware is the matching
        // POSIX TZ string from posix_tz_db.js (e.g. "EST5EDT,M3.2.0,M11.1.0" for
        // "America/New_York") - the format a configTzTime()-style firmware API needs.
        firmware_name: '|*TZ*|',
        readable_name: 'Timezone',
        type: 'timezone',
        max_length: 64
    }
]
```

```cpp
// In your ESP32 code, `|*TZ*|` gets patched with a POSIX TZ string, so use it directly
// with the framework's timezone-aware NTP setup, e.g. on the ESP32 Arduino core:
const char POSIX_TZ[64] = "|*TZ*|";
configTzTime(POSIX_TZ, "pool.ntp.org");
```

### Variable Replacement Details

- **Placeholders**: Use unique strings (e.g., `|*VAR*|`) that won't appear elsewhere in your firmware
- **Max Length**: Must match the size allocated in your ESP32 code - big enough to hold both the
  placeholder string itself and the longest value you'll ever substitute in (usually 100 bytes for
  free text; a handful of bytes is enough for a short `type: 'enum'` value; 64 bytes comfortably
  covers every `type: 'timezone'` POSIX string, the longest of which is ~44 bytes)
- **Padding**: Values are automatically null-padded to `max_length`
- **Enum type**: Set `type: 'enum'` and provide an `options` array (each either a plain string, or
  `{value, label}` if the displayed label should differ from what's written into the firmware) to
  render a dropdown instead of a free-text field
- **Timezone type**: Set `type: 'timezone'` for a dropdown of every IANA timezone, auto-selecting
  the browser's detected zone by default. No `options` needed - the list comes from the browser
  itself, and the selected IANA name is converted to a POSIX TZ string (via the bundled
  `posix_tz_db.js`) right before it's written into firmware
- **Integrity**: Checksum and SHA256 are automatically recalculated after replacement
- **Storage**: User values are saved in browser localStorage with key `fw_var_<firmware_name>`
  (for `type: 'timezone'`, this stores the IANA name, e.g. `"America/New_York"`, not the POSIX string)

### Testing Your Configuration

1. Start a local server:
   ```bash
   python3 -m http.server 8080
   ```

2. Open `http://localhost:8080` in Chrome/Edge

3. Select your new firmware from the dropdown

4. Verify that:
   - Firmware files load without errors (check console)
   - Variables appear in the configuration section
   - Values persist after page reload
   - Flashing completes successfully

### Wizard vs Index Interface

Both interfaces use the same `config.js` file, but display different fields:

- **wizard.html** uses: `name`, `description`, `expectedBehavior`, `files`, `variables`
- **index.html** uses: `name`, `files`, `variables`

The `expectedBehavior` array supports variable placeholders (e.g., `|*S*|`) which get replaced with actual user values in the wizard's final step.

## Credits

Based on:
- [ESPWebTool](https://github.com/SpacehuhnTech/espwebtool) by Spacehuhn
- [esp-web-flasher](https://github.com/NabuCasa/esp-web-flasher) by NabuCasa
- [esptool-js](https://github.com/espressif/esptool-js) by Espressif

## Local Development

To run locally:

```bash
# Start a local HTTP server
python3 -m http.server 8080

# Open in browser
open http://localhost:8080
```

## Browser Compatibility

| Browser | Supported |
|---------|-----------|
| Chrome  | ✅ Yes    |
| Edge    | ✅ Yes    |
| Opera   | ✅ Yes    |
| Firefox | ❌ No     |
| Safari  | ❌ No     |

## Troubleshooting

**Device not detected?**
- Make sure your device is connected via USB
- Try a different USB cable
- Make sure that the vendor id of the device is added to the filter. To show the vendor ID of a device; open the console in the brower and paste `navigator.serial.requestPort().then(x => console.log(x,x.getInfo()))` this will give you the device and vendor ID of your device.

**Flash fails?**
- Try disconnecting and reconnecting
- Check the console output for detailed error messages
- Ensure the firmware files are accessible
- `index.html`'s Connect button just opens the port - it doesn't touch the device's boot
  state. Flash Device is what pulses it into bootloader mode and syncs, every time (not
  just the first) - if that fails with "No serial data received", the device didn't
  respond to the automatic reset-into-bootloader attempt; put it in boot mode manually
  (hold BOOT, press RESET, release both) and try again

**Variables not being replaced?**
- Make sure you've entered values in the configuration fields
- Check that the firmware supports variable replacement (look for the "Variables" section)
- Verify the console output shows "Replacing variables in firmware..."

**Device doesn't reboot into the new firmware after flashing?**
- Both `index.html` and `wizard.html` try an automatic reset once flashing finishes, by
  pulsing the RTS line directly (assert, wait, release) via `Transport.setRTS()`. This
  is deliberately *not* `esploader.after('hard_reset', ...)` from esptool-js - that
  method only ever *releases* RTS, assuming it's already asserted from an earlier step;
  in practice that assumption doesn't always hold, and it reports success while the
  device stays in bootloader mode until a manual power cycle. The explicit pulse
  sequence here matches what's confirmed working by other web flashers (e.g.
  [ESPConnect](https://github.com/thelastoutpostworkshop/ESPConnect)). If it still
  doesn't take on some board/browser combination, just press the physical RESET button.

