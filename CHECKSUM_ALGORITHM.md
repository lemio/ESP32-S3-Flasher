# Checksum Algorithm: How ESP32 Firmware Integrity Works

> **Audience:** First-year computer science students who want to understand how embedded firmware integrity works — and how this flasher tool re-applies it after modifying a binary.

---

## Table of Contents

1. [Why Do Firmware Images Need a Checksum?](#1-why-do-firmware-images-need-a-checksum)
2. [The ESP32 App Image Format](#2-the-esp32-app-image-format)
   - [The Image Header](#21-the-image-header)
   - [The Extended Image Header](#22-the-extended-image-header)
   - [Segment Headers and Data](#23-segment-headers-and-data)
3. [The XOR Checksum Algorithm](#3-the-xor-checksum-algorithm)
4. [The SHA-256 Hash Digest](#4-the-sha-256-hash-digest)
5. [Variable Replacement and Why Integrity Must Be Recalculated](#5-variable-replacement-and-why-integrity-must-be-recalculated)
6. [How This Tool Recalculates Integrity Step by Step](#6-how-this-tool-recalculates-integrity-step-by-step)
7. [How Other Architectures Handle This](#7-how-other-architectures-handle-this)
8. [Further Reading](#8-further-reading)

---

## 1. Why Do Firmware Images Need a Checksum?

When a microcontroller is manufactured and firmware is written to its flash memory, there is always a small risk that:

- A bit gets flipped during programming (hardware noise, power fluctuation).
- The flash storage cell degrades over time.
- Firmware is accidentally corrupted during an over-the-air update.

Without a way to *detect* corruption, the chip would silently run broken code — leading to unpredictable behaviour, crashes, or security vulnerabilities.

A **checksum** (or **hash**) is a short value computed from the firmware data. If even a single byte changes, the checksum changes too. At startup, the chip re-computes the checksum from what is stored in flash and compares it to the stored value. If they don't match, the bootloader refuses to run the image.

Think of it like a "fingerprint" for your firmware — any alteration changes the fingerprint.

> **Reference:** [ESP-IDF Startup Flow](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/startup.html)

---

## 2. The ESP32 App Image Format

The ESP32 uses a specific binary format for its application images. Understanding this format is essential for understanding how and where the checksum is stored.

> **Reference:** [ESP32 App Image Format](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/app_image_format.html)

The image is structured as follows:

```
┌──────────────────────────────┐  Byte 0
│       Image Header (8 B)     │
├──────────────────────────────┤  Byte 8
│  Extended Image Header (16 B)│
├──────────────────────────────┤  Byte 24
│    Segment 0 Header (8 B)    │
│    Segment 0 Data (N bytes)  │
├──────────────────────────────┤
│    Segment 1 Header (8 B)    │
│    Segment 1 Data (N bytes)  │
│             ...              │
├──────────────────────────────┤
│  Padding to 16-byte boundary │
│  + 1 byte XOR Checksum       │
├──────────────────────────────┤  (optional)
│  32-byte SHA-256 Digest      │
└──────────────────────────────┘
```

### 2.1 The Image Header

The first 8 bytes of the image form the **Image Header**:

| Byte | Field              | Meaning                                         |
|------|--------------------|-------------------------------------------------|
| 0    | `magic`            | Always `0xE9` — identifies this as an ESP32 image |
| 1    | `segment_count`    | Number of segments in the image                 |
| 2    | `spi_mode`         | SPI flash mode (e.g., DIO, QIO)                 |
| 3    | `spi_speed_size`   | SPI speed and flash size                        |
| 4–7  | `entry_addr`       | Address where execution starts (32-bit, little-endian) |

The magic byte `0xE9` is the very first thing the bootloader checks. If it doesn't see `0xE9` at byte 0, it knows this is not a valid ESP32 image and refuses to boot it.

```javascript
// From index.html / wizard.html — validate magic byte before processing
if (binaryString.charCodeAt(0) !== 0xE9) {
    log('Not a valid ESP32 image, skipping integrity recalculation', 'warning');
    return binaryString;
}
```

### 2.2 The Extended Image Header

Bytes 8–23 form the **Extended Image Header** (16 bytes):

| Byte  | Field               | Meaning                                                        |
|-------|---------------------|----------------------------------------------------------------|
| 8     | `wp_pin`            | Write-protect pin config (1 byte)                              |
| 9–11  | `spi_pin_drv`       | SPI pin drive settings (3 bytes)                               |
| 12–13 | `chip_id`           | Target chip identifier (2 bytes, e.g., `0x0009` = ESP32-S3)   |
| 14    | `min_chip_rev`      | Minimum chip revision required (legacy, 1 byte)                |
| 15–16 | `min_chip_rev_full` | Minimum chip revision (2 bytes, major × 100 + minor)           |
| 17–18 | `max_chip_rev_full` | Maximum chip revision (2 bytes, major × 100 + minor)           |
| 19–22 | `reserved`          | Reserved bytes (must be zero, 4 bytes)                         |
| 23    | `hash_appended`     | If `1`, a SHA-256 digest follows the XOR checksum (1 byte)     |

<details>
<summary>Known <code>chip_id</code> values (click to expand)</summary>

| `chip_id` value | Chip        |
|-----------------|-------------|
| `0x0000`        | ESP32       |
| `0x0002`        | ESP32-S2    |
| `0x0005`        | ESP32-C3    |
| `0x0009`        | ESP32-S3    |
| `0x000C`        | ESP32-C2    |
| `0x000D`        | ESP32-C6    |
| `0x0010`        | ESP32-H2    |
| `0x0012`        | ESP32-P4    |
| `0x0014`        | ESP32-C61   |
| `0x0017`        | ESP32-C5    |
| `0x0019`        | ESP32-H21   |
| `0x001C`        | ESP32-H4    |
| `0x0020`        | ESP32-S31   |
| `0xFFFF`        | Invalid     |

> **Reference:** [`esp_chip_id_t` in ESP-IDF](https://github.com/espressif/esp-idf/blob/master/components/bootloader_support/include/esp_app_format.h)

</details>

Byte 23 (`hash_appended`) tells us whether a SHA-256 digest has been appended to the image:

```javascript
// From index.html — read the hash_appended flag from the extended header
const appendDigest = binaryString.charCodeAt(23);
const hasSHA256 = binaryString.length >= 33 &&
                 binaryString.length % 16 === 0 &&
                 appendDigest !== 0x00;
```

### 2.3 Segment Headers and Data

After the two headers (24 bytes total), the file contains a series of **segments**. Each segment represents a region of memory — such as code (`.text`), read-only data (`.rodata`), or initialised data (`.data`).

Each segment begins with an **8-byte segment header**:

| Byte | Field         | Meaning                                         |
|------|---------------|-------------------------------------------------|
| 0–3  | `load_addr`   | Target RAM/flash address (32-bit, little-endian)|
| 4–7  | `data_length` | Length of segment data in bytes (32-bit, little-endian) |

Immediately after the 8-byte header comes the actual segment data (`data_length` bytes).

Reading `data_length` in little-endian:

```javascript
// From index.html / wizard.html — read a 32-bit little-endian length
const segDataLen = binaryString.charCodeAt(offset + 4) |
                  (binaryString.charCodeAt(offset + 5) << 8) |
                  (binaryString.charCodeAt(offset + 6) << 16) |
                  (binaryString.charCodeAt(offset + 7) << 24);
```

> **Little-endian** means the least significant byte comes first in memory. So the value `0x00001000` (4096 in decimal) is stored as the four bytes `00 10 00 00`.

---

## 3. The XOR Checksum Algorithm

The ESP32 uses a simple but effective **XOR checksum** over all segment data bytes.

### The Algorithm in Plain English

1. Start with the seed value `0xEF`.
2. For every segment in the image:
   a. Skip the 8-byte segment header.
   b. XOR each data byte into the running checksum.
3. The final value (a single byte, 0–255) is the checksum.
4. This checksum is stored as the last byte before any SHA-256 digest.

### Why XOR?

XOR (exclusive-or) is a bitwise operation. `A XOR B` returns 1 for each bit position where A and B differ, and 0 where they are the same. Chaining XOR operations over many bytes is:

- **Simple** — one instruction on any processor.
- **Reversible** — `A XOR A = 0`, so any byte XOR'd with itself cancels out.
- **Cumulative** — the order of inputs doesn't affect the result.
- **Good enough for corruption detection** — a single flipped bit changes the checksum.

| Operation | Value (hex) | Value (binary) |
|-----------|-------------|----------------|
| Initial seed | `0xEF` | `1110 1111` |
| XOR byte `0x01` | `0xEE` | `1110 1110` |
| XOR byte `0x02` | `0xEC` | `1110 1100` |

### The Code

```javascript
// From index.html and wizard.html — calculateChecksum()
const calculateChecksum = (binaryString) => {
    // Read segment count from the image header (byte 1)
    const segmentCount = binaryString.charCodeAt(1);

    // Start with the seed value defined by ESP-IDF
    let checksum = 0xEF;

    // Skip the 8-byte image header + 16-byte extended header = 24 bytes
    let offset = 24;

    for (let i = 0; i < segmentCount; i++) {
        // Read this segment's data length (bytes 4–7 of segment header, little-endian)
        const segDataLen = binaryString.charCodeAt(offset + 4) |
                          (binaryString.charCodeAt(offset + 5) << 8) |
                          (binaryString.charCodeAt(offset + 6) << 16) |
                          (binaryString.charCodeAt(offset + 7) << 24);

        // Move past the 8-byte segment header
        offset += 8;

        // XOR each data byte into the checksum
        for (let j = 0; j < segDataLen; j++) {
            checksum ^= binaryString.charCodeAt(offset + j);
        }

        // Move past the segment data to the next segment header
        offset += segDataLen;
    }

    return checksum; // A single byte value, 0–255
};
```

### Step-by-Step Walkthrough (Small Example)

Suppose we have an image with **one segment** containing four data bytes: `[0xAA, 0xBB, 0xCC, 0xDD]`.

```
Step 0: checksum = 0xEF  (seed)
Step 1: checksum = 0xEF ^ 0xAA = 0x45
Step 2: checksum = 0x45 ^ 0xBB = 0xFE
Step 3: checksum = 0xFE ^ 0xCC = 0x32
Step 4: checksum = 0x32 ^ 0xDD = 0xEF   ← stored at the end of the image
```

---

## 4. The SHA-256 Hash Digest

Modern ESP-IDF versions (and the ESP32-S3 in particular) optionally append a **SHA-256 hash** of the entire image after the XOR checksum.

SHA-256 (Secure Hash Algorithm, 256-bit output) is a **cryptographic hash function**. Unlike XOR:
- It produces a 32-byte (256-bit) output from any length of input.
- It is computationally infeasible to construct two different inputs with the same output.
- Changing even a single bit in the input completely changes the output (the **avalanche effect**).

> **Reference:** [SHA-2 on Wikipedia](https://en.wikipedia.org/wiki/SHA-2)

### How to Detect Whether a SHA-256 Digest Is Present

The image has a SHA-256 digest appended if **all** of the following are true:

1. The image length is a multiple of 16 bytes (the image is padded).
2. The image length is at least 33 bytes.
3. Byte 23 of the extended header (`hash_appended`) is non-zero.

```javascript
// From index.html — detect SHA-256 presence
const appendDigest = binaryString.charCodeAt(23);
const hasSHA256 = binaryString.length >= 33 &&
                 binaryString.length % 16 === 0 &&
                 appendDigest !== 0x00;
```

### Calculating the SHA-256 Hash

The SHA-256 digest is computed over the image *without* the existing 32-byte digest at the end. Modern browsers expose this via the [Web Crypto API](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest):

```javascript
// From index.html / wizard.html — recalculate SHA-256 after updating the checksum

// Convert the binary string to a typed byte array
const dataArray = binaryUtils.stringToArrayBuffer(rebuiltImage);

// Ask the browser's built-in crypto engine to compute SHA-256
const hashBuffer = await crypto.subtle.digest('SHA-256', dataArray);

// Convert the 32-byte hash back to a string for appending
const hashArray = new Uint8Array(hashBuffer);
const hashString = String.fromCharCode(...hashArray);

// Append the 32 bytes to the image
rebuiltImage += hashString;
```

The `crypto.subtle.digest` call is asynchronous (hence `await`) because hashing large images can take a moment. The browser hardware-accelerates this using native instructions.

---

## 5. Variable Replacement and Why Integrity Must Be Recalculated

This flasher tool allows you to **embed configuration variables directly in the firmware binary** — things like a WiFi password or a device name. At flash time, the tool replaces placeholder strings with the user's values.

### How Placeholder Variables Work in the Firmware Source (ESP-IDF / Arduino)

In your ESP32 C++ code, you reserve a fixed-size buffer and fill it with a recognisable placeholder:

```cpp
// In your ESP32 firmware source code
const char WIFI_SSID[100] = "|*S*|";
const char WIFI_PASS[100] = "|*P*|";
const char MDNS_HOST[100] = "|*M*|";
```

The compiler compiles this as-is into the `.rodata` segment of the binary. The 100-byte arrays are stored verbatim in flash memory.

> **Reference:** [ESP-IDF Partition Tables](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/partition-tables.html)

### How the Tool Replaces Variables

1. **Find** the placeholder string (e.g., `|*S*|`) in the binary image.
2. **Replace** the entire 100-byte padded region with the new value, null-terminated and padded to 100 bytes.
3. **Recalculate** the XOR checksum (because segment data changed).
4. **Recalculate** the SHA-256 digest (because the image changed).

After step 2, the existing XOR checksum byte and SHA-256 digest in the image are **no longer valid** — they were computed over the original placeholder strings. If we flashed the image as-is, the bootloader would reject it.

This is the core problem this tool solves: **we are intentionally modifying the firmware binary, so we must re-sign it**.

---

## 6. How This Tool Recalculates Integrity Step by Step

The `recalculateFirmwareIntegrity` function in both `index.html` and `wizard.html` orchestrates the full process:

```javascript
const recalculateFirmwareIntegrity = async (binaryString) => {
    // ── Step 1: Validate magic byte ──────────────────────────────────────
    // Only proceed if this is a valid ESP32 image.
    if (binaryString.charCodeAt(0) !== 0xE9) {
        log('Not a valid ESP32 image, skipping integrity recalculation', 'warning');
        return binaryString;
    }

    // ── Step 2: Detect SHA-256 presence ──────────────────────────────────
    // Byte 23 is the hash_appended flag in the extended header.
    const appendDigest = binaryString.charCodeAt(23);
    const hasSHA256 = binaryString.length >= 33 &&
                     binaryString.length % 16 === 0 &&
                     appendDigest !== 0x00;

    log(`Recalculating integrity (SHA256: ${hasSHA256})`, 'info');

    // ── Step 3: Strip the old SHA-256 digest (if present) ────────────────
    // Work on the image *without* the trailing 32-byte hash,
    // because the hash is computed over everything before it.
    const imageData = hasSHA256
        ? binaryString.substring(0, binaryString.length - 32)
        : binaryString;

    // ── Step 4: Recalculate the XOR checksum ─────────────────────────────
    // We pass `binaryString` (not `imageData`) because calculateChecksum()
    // only reads exactly segmentCount segments — it stops after the last
    // segment data byte and never reaches the trailing SHA-256 digest.
    // The result is identical to passing imageData; binaryString is passed
    // here to match the original source exactly.
    const newChecksum = calculateChecksum(binaryString);

    // Replace the last byte of imageData with the new checksum.
    // The checksum is stored as the last byte of the padded image (before SHA-256).
    let rebuiltImage = imageData.substring(0, imageData.length - 1) +
                       String.fromCharCode(newChecksum);

    log(`Checksum updated: 0x${newChecksum.toString(16).toUpperCase()}`, 'success');

    // ── Step 5: Recalculate the SHA-256 digest (if needed) ───────────────
    if (hasSHA256) {
        const dataArray = binaryUtils.stringToArrayBuffer(rebuiltImage);
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataArray);
        const hashArray = new Uint8Array(hashBuffer);
        const hashString = String.fromCharCode(...hashArray);
        rebuiltImage += hashString;
        log('SHA256 recalculated', 'success');
    }

    return rebuiltImage;
};
```

### Visual Summary

```
Original image (from server):
┌─────────────────────────────┬────────────┬────────────────────────┐
│  Headers + Segments + Pad   │ Checksum   │  SHA-256 (32 bytes)    │
│  (with placeholder values)  │ (old, 1 B) │  (old, covers image)   │
└─────────────────────────────┴────────────┴────────────────────────┘

After variable replacement:
┌─────────────────────────────┬────────────┬────────────────────────┐
│  Headers + Segments + Pad   │ Checksum   │  SHA-256 (32 bytes)    │
│  (with REAL values)         │ (WRONG!)   │  (WRONG!)              │
└─────────────────────────────┴────────────┴────────────────────────┘

After recalculation:
┌─────────────────────────────┬────────────┬────────────────────────┐
│  Headers + Segments + Pad   │ Checksum   │  SHA-256 (32 bytes)    │
│  (with REAL values)         │ (new, 1 B) │  (new, covers image)   │
└─────────────────────────────┴────────────┴────────────────────────┘
```

---

## 7. How Other Architectures Handle This

Checksum and integrity schemes vary widely across microcontroller families. Here is a comparison:

### ESP32 Family

All variants (ESP32, ESP32-S2, ESP32-S3, ESP32-C3, etc.) use the same image format described above: an XOR checksum over segment data, optionally followed by a SHA-256 digest. The exact location of the checksum (last byte before the digest) and the seed value (`0xEF`) are consistent across the family.

> Newer ESP-IDF versions also support **secure boot** with RSA or ECDSA image signing — in that case, an additional signature block is appended after the SHA-256 digest. However, this tool does not modify secure-boot-signed images.

### AVR (Arduino Uno, Mega, etc.)

AVR microcontrollers (used by most classic Arduino boards) typically do **not** have hardware-enforced image checksums. The bootloader (e.g., Optiboot) uses a simple CRC-16 check on incoming Intel HEX data during programming, but the application image in flash is not verified at every startup.

Optionally, you can add your own startup integrity check in firmware using a stored CRC, but it is not enforced by the bootloader by default.

```c
// Example: CRC-16/CCITT check you might add yourself to an AVR project
uint16_t crc = 0xFFFF;
for (uint16_t i = 0; i < firmware_size; i++) {
    crc ^= (uint16_t)pgm_read_byte(i) << 8;
    for (uint8_t j = 0; j < 8; j++) {
        if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
        else crc <<= 1;
    }
}
// Compare with stored CRC at end of flash
```

This is fundamentally different from the ESP32 approach: the AVR bootloader trusts whatever is in flash, whereas the ESP32 bootloader verifies the image on every boot.

### STM32 (ST Microelectronics ARM Cortex-M)

STM32 microcontrollers are more similar in capability to the ESP32. They use ARM Cortex-M cores and store firmware in internal flash. STM32 firmware images are typically plain binary or Intel HEX — there is **no built-in image checksum** in the standard firmware format.

However:
- **CRC verification** can be done in software using the STM32's hardware CRC peripheral (CRC-32, polynomial `0x04C11DB7`).
- **Secure Boot** on STM32 (via the TrustZone or SBSFU framework) adds ECDSA or RSA signature verification similar to ESP32 secure boot.
- **STM32's Option Bytes** can store a checksum of flash content that is verified at boot, but this is chip-specific and not part of the standard binary format.

A practical difference: when you patch an STM32 binary, you do **not** need to recalculate a checksum unless you explicitly added one yourself. This makes patching easier but also less safe.

### Summary Table

| Feature                        | ESP32 / ESP32-S3         | AVR (Classic Arduino)  | STM32                        |
|--------------------------------|--------------------------|------------------------|------------------------------|
| Magic byte / image header      | ✅ `0xE9`               | ❌                     | ❌ (plain binary)            |
| Startup XOR checksum           | ✅ Required              | ❌                     | ❌ (optional, user code)     |
| SHA-256 hash on boot           | ✅ Optional              | ❌                     | ❌ (only with SBSFU)         |
| Secure boot (signature)        | ✅ Optional              | ❌                     | ✅ Optional (SBSFU / TZ)     |
| Must recalculate after patch?  | ✅ **Yes**               | ❌ Not required        | ❌ Only if you added your own |

---

## 8. Further Reading

| Topic | Link |
|-------|------|
| ESP-IDF Startup & Boot Flow | https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/startup.html |
| ESP32 App Image Binary Format | https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/app_image_format.html |
| ESP32 Partition Tables | https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/partition-tables.html |
| SHA-2 (SHA-256) Algorithm | https://en.wikipedia.org/wiki/SHA-2 |
| Web Crypto API — `subtle.digest` | https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest |
| ESP-IDF Secure Boot | https://docs.espressif.com/projects/esp-idf/en/stable/esp32/security/secure-boot-v2.html |
| XOR and Bitwise Operations | https://en.wikipedia.org/wiki/Bitwise_operation#XOR |
| Little-endian vs Big-endian | https://en.wikipedia.org/wiki/Endianness |
| CRC Algorithms (AVR/STM32 context) | https://en.wikipedia.org/wiki/Cyclic_redundancy_check |
