#!/usr/bin/env python3
"""
Debug the firmware reconstruction issue by manually simulating what JavaScript should do.
"""

def reconstruct_firmware(original_file, modified_file):
    """Simulate the JavaScript reconstruction logic"""
    
    with open(original_file, 'rb') as f:
        original = f.read()
    
    with open(modified_file, 'rb') as f:
        modified = f.read()
    
    print(f"Original size: {len(original)}")
    print(f"Modified size: {len(modified)}")
    print()
    
    # Check if imageData would be correct (everything except last 32 bytes = SHA256)
    if len(original) >= 33:
        imageData_end = len(original) - 32  # Remove SHA256
        print(f"imageData would be: bytes 0 to {imageData_end} (length {imageData_end})")
        print(f"Last byte of imageData (checksum position): offset {imageData_end - 1}")
        print(f"  Original: 0x{original[imageData_end - 1]:02x}")
        print(f"  Modified: 0x{modified[imageData_end - 1]:02x}")
        print()
    
    # JavaScript: dataBeforeChecksum = imageData.substring(0, imageData.length - 1)
    # This should be everything EXCEPT the last byte of imageData
    dataBeforeChecksum_end = imageData_end - 1
    print(f"dataBeforeChecksum would be: bytes 0 to {dataBeforeChecksum_end} (length {dataBeforeChecksum_end})")
    print()
    
    # JavaScript: rebuiltImage = dataBeforeChecksum + String.fromCharCode(checksum)
    # This should place the NEW checksum at position dataBeforeChecksum_end
    print(f"After adding new checksum byte:")
    print(f"  rebuiltImage length would be: {dataBeforeChecksum_end + 1}")
    print(f"  Checksum would be at position: {dataBeforeChecksum_end} (byte {dataBeforeChecksum_end})")
    print(f"  Checksum in modified file at {dataBeforeChecksum_end}: 0x{modified[dataBeforeChecksum_end]:02x}")
    print()
    
    # JavaScript: rebuiltImage += hashString (32 bytes)
    # This should append 32 bytes of SHA256
    print(f"After appending SHA256:")
    print(f"  Final length would be: {dataBeforeChecksum_end + 1 + 32}")
    print(f"  Checksum would be at position: {dataBeforeChecksum_end}")
    print(f"  Checksum byte -33 from end: position {len(modified) - 33}")
    print(f"  Checksum at position {len(modified) - 33} in modified: 0x{modified[len(modified) - 33]:02x}")
    print()
    
    # Calculate what the NEW checksum should be (over segment DATA only)
    # For now, let's just check what we have
    print("=== POSITIONS IN MODIFIED FILE ===")
    print(f"Position {dataBeforeChecksum_end} (calculated checksum pos): 0x{modified[dataBeforeChecksum_end]:02x}")
    print(f"Position {len(modified) - 33} (byte -33): 0x{modified[len(modified) - 33]:02x}")
    print(f"Position {len(modified) - 1} (last byte): 0x{modified[len(modified) - 1]:02x}")
    print()
    
    # Calculate expected checksum
    print("=== CALCULATING EXPECTED CHECKSUM ===")
    checksum = 0xEF
    
    # Parse ESP32 image header
    if modified[0] != 0xE9:
        print("ERROR: Not a valid ESP32 image (magic byte wrong)")
        return
    
    segment_count = modified[1]
    print(f"Segment count: {segment_count}")
    
    # Skip: 8-byte main header + 16-byte extended header = 24 bytes
    offset = 24
    total_data_bytes = 0
    
    for i in range(segment_count):
        # Read segment header (8 bytes)
        seg_load_addr = int.from_bytes(modified[offset:offset+4], 'little')
        seg_data_len = int.from_bytes(modified[offset+4:offset+8], 'little')
        print(f"Segment {i}: load_addr=0x{seg_load_addr:08x}, data_len={seg_data_len}")
        
        offset += 8  # Skip segment header
        
        # XOR all DATA bytes
        for j in range(seg_data_len):
            checksum ^= modified[offset + j]
        
        offset += seg_data_len
        total_data_bytes += seg_data_len
    
    print(f"Total DATA bytes: {total_data_bytes}")
    print(f"Expected checksum: 0x{checksum:02x}")
    print()
    
    # Now check where this checksum appears in the file
    print(f"=== SEARCHING FOR CHECKSUM VALUE 0x{checksum:02x} ===")
    for i in range(len(modified)):
        if modified[i] == checksum:
            if i >= len(modified) - 40:  # Only show if near the end
                print(f"  Found at position {i} (byte -{len(modified) - i} from end)")

if __name__ == '__main__':
    original = 'Amoled-T-Display/Screencast/Firmware/firmware.bin'
    modified = 'firmware_modified (1).bin'
    
    reconstruct_firmware(original, modified)
