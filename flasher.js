// flasher.js - Shared firmware loading, checksum, and flashing utilities
// Included in both index.html and wizard.html

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const storage = {
    get: (key, defaultValue) => localStorage.getItem(`fw_var_${key}`) ?? defaultValue,
    set: (key, value) => localStorage.setItem(`fw_var_${key}`, value)
};

const binaryUtils = {
    arrayBufferToString: (buffer) => {
        const bytes = new Uint8Array(buffer);
        return Array.from(bytes, byte => String.fromCharCode(byte)).join('');
    },

    stringToArrayBuffer: (str) => {
        const buffer = new Uint8Array(str.length);
        for (let i = 0; i < str.length; i++) {
            buffer[i] = str.charCodeAt(i);
        }
        return buffer;
    }
};

const calculateChecksum = (binaryString) => {
    const segmentCount = binaryString.charCodeAt(1);
    let checksum = 0xEF;
    let offset = 24; // Skip main + extended headers

    for (let i = 0; i < segmentCount; i++) {
        const segDataLen = binaryString.charCodeAt(offset + 4) |
                          (binaryString.charCodeAt(offset + 5) << 8) |
                          (binaryString.charCodeAt(offset + 6) << 16) |
                          (binaryString.charCodeAt(offset + 7) << 24);

        offset += 8; // Skip segment header

        for (let j = 0; j < segDataLen; j++) {
            checksum ^= binaryString.charCodeAt(offset + j);
        }

        offset += segDataLen;
    }

    return checksum;
};

const recalculateFirmwareIntegrity = async (binaryString, logFn = () => {}) => {
    // Validate ESP32 image
    if (binaryString.charCodeAt(0) !== 0xE9) {
        return binaryString;
    }

    const appendDigest = binaryString.charCodeAt(23);
    const hasSHA256 = binaryString.length >= 33 &&
                     binaryString.length % 16 === 0 &&
                     appendDigest !== 0x00;

    // Remove SHA256 if present
    const imageData = hasSHA256 ? binaryString.substring(0, binaryString.length - 32) : binaryString;

    // Calculate and replace checksum
    const newChecksum = calculateChecksum(binaryString);
    let rebuiltImage = imageData.substring(0, imageData.length - 1) + String.fromCharCode(newChecksum);

    logFn(`Checksum updated: 0x${newChecksum.toString(16).toUpperCase()}`, 'success');

    // Recalculate SHA256 if needed
    if (hasSHA256) {
        const dataArray = binaryUtils.stringToArrayBuffer(rebuiltImage);
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataArray);
        const hashArray = new Uint8Array(hashBuffer);
        const hashString = String.fromCharCode(...hashArray);
        rebuiltImage += hashString;
        logFn('SHA256 recalculated', 'success');
    }

    return rebuiltImage;
};

const loadFirmware = async (path) => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Failed to load ${path}`);
    const buffer = await response.arrayBuffer();
    return binaryUtils.arrayBufferToString(buffer);
};

// logFn(message, level) where level is 'info', 'warning', or 'success'
const replaceVariables = async (binaryString, variables, logFn = () => {}) => {
    let modified = binaryString;
    const warnings = [];
    let changeCount = 0;

    for (const variable of variables) {
        const input = document.querySelector(`[data-firmware-name="${variable.firmware_name}"]`);
        if (!input) continue;

        const value = input.value;
        const searchString = variable.firmware_name;
        const maxLen = variable.max_length || 100;

        let searchIndex = modified.indexOf(searchString);
        if (searchIndex === -1) {
            warnings.push(`Variable '${searchString}' not found in firmware`);
            continue;
        }

        // Create padded replacement
        let replacement = value + '\0';
        while (replacement.length < maxLen) replacement += '\0';
        if (replacement.length > maxLen) {
            replacement = replacement.substring(0, maxLen);
            warnings.push(`Value '${variable.readable_name}' truncated to ${maxLen} bytes`);
        }

        // Replace all occurrences
        let occurrences = 0;
        while (searchIndex !== -1) {
            const original = modified.substring(searchIndex, searchIndex + maxLen);
            if (replacement !== original) {
                modified = modified.substring(0, searchIndex) + replacement + modified.substring(searchIndex + maxLen);
                occurrences++;
                changeCount++;
            }
            searchIndex = modified.indexOf(searchString, searchIndex + maxLen);
        }

        if (occurrences > 0) {
            logFn(`Replaced '${searchString}' at ${occurrences} location(s)`, 'info');
        }
    }

    warnings.forEach(w => logFn(w, 'warning'));

    // Recalculate integrity if modified
    if (changeCount > 0) {
        logFn('Recalculating firmware integrity...', 'info');
        modified = await recalculateFirmwareIntegrity(modified, logFn);
    }

    return modified;
};

export { sleep, storage, binaryUtils, calculateChecksum, recalculateFirmwareIntegrity, loadFirmware, replaceVariables };
