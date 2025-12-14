# ESP32-S3 Web Flasher

A simple, browser-based tool for flashing ESP32-S3 devices using the Web Serial API. Built with the ESPtool-js library made by [Esperessif](https://github.com/espressif/esptool-js). Next to flashing it can also alter the firmware by replacing *magic* keywords with other content; this could be usefull for wifi setup or other settings that you want end-users to change.

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

## Requirements

- A modern browser with Web Serial API support:
  - Google Chrome (version 89+)
  - Microsoft Edge (version 89+)
  - Opera (version 75+)
- ESP32-S3 device connected via USB
- Device must be in download mode

## Usage

1. **Open the flasher**: Open `index.html` in a supported browser
2. **Select firmware**: Choose the firmware you want to flash from the dropdown
3. **Configure variables** (if available): Enter your WiFi SSID, password, and mDNS hostname
4. **Connect device**: Click "Connect to ESP32-S3" and select your device from the browser popup
5. **Flash**: Click "Flash Device" to start the flashing process

## Available Firmware

- **Amoled T-Display - Factory Firmware**: Factory firmware for the LilyGo Amoled T-Display board
- **Amoled T-Display - Screencast**: Screencast firmware with configurable WiFi credentials
  - Variables: WiFi SSID, WiFi Password, mDNS Hostname

## How It Works

This tool uses:
- [esptool](https://github.com/espressif/esptool-js) -  JavaScript implementation of esptool
- Web Serial API - For communicating with the ESP32-S3 over USB
- Web Crypto API - For SHA256 hash recalculation

### Variable Replacement

For firmware with configurable variables:
1. Variables are marked with special delimiters (e.g., `|*S*|` for SSID) in 100-byte padded regions
2. When you enter values, they replace the entire 100-byte region
3. The firmware checksum is automatically recalculated over segment data only (see [CHECKSUM_ALGORITHM.md](CHECKSUM_ALGORITHM.md))
4. If present, the SHA256 digest is recalculated and appended

### Flashing Process

The firmware is loaded from the repository and flashed to the following addresses:
- `0x0000`: bootloader.bin
- `0x8000`: partitions.bin
- `0xe000`: boot_app0.bin
- `0x10000`: firmware.bin (with variable replacements if configured)

## Technical Documentation

For detailed information about the ESP32 firmware checksum algorithm, see [CHECKSUM_ALGORITHM.md](CHECKSUM_ALGORITHM.md).

**Key insight**: The ESP32 checksum is calculated only over segment DATA bytes, not headers or padding. This was discovered through extensive reverse-engineering and validation against esptool.

## Configure it for your own project

All firmware configurations and device settings are now centralized in `config.js`, making it easy to add your own firmware or devices.

### Configuration File Structure

The `config.js` file contains two main objects:

#### 1. **CONFIG** - General device settings

```javascript
const CONFIG = {
    DISCONNECT_WAIT_MS: 1500,      // Wait time after disconnect
    BAUD_RATE: 115200,              // Serial communication speed
    CHIP_NAME: "ESP32-S3",          // Target chip type
    FILTERS: [                      // USB vendor IDs for device detection
        {usbVendorId: 0x10C4},      // SILICON_LABS
        {usbVendorId: 0x303A},      // ESPRESSIF
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
Then add it to the `FILTERS` array.

#### 2. **FIRMWARE_CONFIGS** - Firmware definitions

Each firmware configuration has the following structure:

```javascript
'firmware-key': {
    name: 'Human-readable name',
    description: 'Brief description (wizard only)',
    expectedBehavior: [              // Array of expected behaviors (wizard only)
        'What happens after flashing',
        'Can include HTML like <b>bold</b> or <a href="...">links</a>'
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
        }
    ]
}
```

### Adding Your Own Firmware

1. **Prepare your firmware files:**
   - Place them in a subdirectory (e.g., `MyDevice/Firmware/`)
   - You'll need: `bootloader.bin`, `partitions.bin`, `boot_app0.bin`, `firmware.bin`
   - You can find them in the subfolder of platformIO project; for example `LilyGo-AMOLED-WebJPEG/.pio/build/T-Display-AMOLED/firmware.bin` 
   - Only the `boot_app0.bin` you can find in `~/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin` on mac
   - To find these files you can use the *Verbose Upload* option in platformIO

2. **Add configuration to `config.js`:**

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
    }
]
```

### Variable Replacement Details

- **Placeholders**: Use unique strings (e.g., `|*VAR*|`) that won't appear elsewhere in your firmware
- **Max Length**: Must match the size allocated in your ESP32 code (usually 100 bytes)
- **Padding**: Values are automatically null-padded to `max_length`
- **Integrity**: Checksum and SHA256 are automatically recalculated after replacement
- **Storage**: User values are saved in browser localStorage with key `fw_var_<firmware_name>`

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
- Ensure the device is in download mode (hold BOOT button while pressing RESET)
- Make sure that the vendor id of the device is added to the filter. To show the vendor ID of a device; open the console in the brower and paste `navigator.serial.requestPort().then(x => console.log(x,x.getInfo()))` this will give you the device and vendor ID of your device.

**Flash fails?**
- Try disconnecting and reconnecting
- Check the console output for detailed error messages
- Ensure the firmware files are accessible

**Variables not being replaced?**
- Make sure you've entered values in the configuration fields
- Check that the firmware supports variable replacement (look for the "Variables" section)
- Verify the console output shows "Replacing variables in firmware..."

## License

This project uses firmware from LilyGo's AMOLED series devices.
