# ESP32-S3 Web Flasher

A simple, browser-based tool for flashing ESP32-S3 devices using the Web Serial API.

## Features

- 🌐 **Browser-based**: No need to install drivers or tools
- 🚀 **Easy to use**: Simple 3-step process to flash your device
- 📱 **Multiple firmware support**: Select from available firmware options
- 📊 **Real-time progress**: Visual feedback during the flashing process
- 🔒 **Secure**: All processing happens locally in your browser

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
3. **Connect device**: Click "Connect to ESP32-S3" and select your device from the browser popup
4. **Flash**: Click "Flash Device" to start the flashing process

## Available Firmware

- **Amoled T-Display - Factory Firmware**: Factory firmware for the LilyGo Amoled T-Display board

## How It Works

This tool uses:
- [esptool-js](https://github.com/espressif/esptool-js) - JavaScript implementation of esptool
- Web Serial API - For communicating with the ESP32-S3 over USB

The firmware is loaded from the repository and flashed to the following addresses:
- `0x0000`: bootloader.bin
- `0x8000`: partitions.bin
- `0xe000`: boot_app0.bin
- `0x10000`: firmware.bin

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

## License

This project uses firmware from LilyGo's AMOLED series devices.
