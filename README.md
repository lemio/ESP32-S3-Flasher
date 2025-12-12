# ESP32-S3 Web Flasher

A simple, browser-based tool for flashing ESP32-S3 devices using the Web Serial API. Built with the ESP Web Flasher library used by [ESPWebTool](https://github.com/SpacehuhnTech/espwebtool).

## Features

- 🌐 **Browser-based**: No need to install drivers or tools
- 🚀 **Easy to use**: Simple process to flash your device
- 📱 **Multiple firmware support**: Select from available firmware options
- 🔧 **Dynamic configuration**: Replace WiFi SSID, password, and mDNS hostname before flashing
- 💾 **Persistent settings**: Configuration values saved in browser localStorage
- 🔒 **Firmware integrity**: Automatic checksum and SHA256 recalculation
- 📊 **Real-time progress**: Visual feedback during the flashing process
- 🔐 **Secure**: All processing happens locally in your browser
- ⚡ **Modern**: Uses the latest esp-web-flasher library (v9.1.0)

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
- [esp-web-flasher](https://github.com/NabuCasa/esp-web-flasher) v9.1.0 - JavaScript implementation of esptool (same library used by ESPWebTool)
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
