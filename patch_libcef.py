"""Re-enable Chromium command-line switches in Ubisoft Connect's libcef.dll.

Port of CrossOver's "CW HACK 25737" (CrossOver 26 sources, dlls/ntdll/loader.c).
Ubisoft Connect sets cef_settings_t.command_line_args_disabled, so libcef ignores the
switches the CrossOver-based engine adds to upc.exe (--in-process-gpu --disable-gpu).
Without them every CEF renderer hits a CHECK and the window stays empty.
The patch forces the flag to 0. It only matches 32-bit libcef 135.0.20.

usage: python3 patch_libcef.py <libcef.dll>
exit: 0 patched or already patched, 2 unknown libcef build, 1 file error
"""
import struct
import sys

RVA = 0x11E92D
BEFORE = bytes.fromhex("8b4734" "894634" "8b4738" "894638")  # mov eax,[edi+0x38]
AFTER = bytes.fromhex("8b4734" "894634" "31c090" "894638")   # xor eax,eax; nop


def rva_to_file_offset(image, rva):
    try:
        pe = struct.unpack_from("<I", image, 0x3C)[0]
        if image[pe:pe + 4] != b"PE\0\0":
            return None
        sections = struct.unpack_from("<H", image, pe + 6)[0]
        table = pe + 24 + struct.unpack_from("<H", image, pe + 20)[0]
        for i in range(sections):
            virtual_size, virtual_address, _, raw_pointer = struct.unpack_from("<IIII", image, table + 40 * i + 8)
            if virtual_address <= rva < virtual_address + virtual_size:
                return raw_pointer + rva - virtual_address
    except struct.error:
        return None
    return None


def patch(image):
    """Patch `image` (bytearray) in place. Returns "patched", "already" or "unknown"."""
    offset = rva_to_file_offset(image, RVA)
    if offset is None or offset + len(BEFORE) > len(image):
        return "unknown"
    current = bytes(image[offset:offset + len(BEFORE)])
    if current == AFTER:
        return "already"
    if current != BEFORE:
        return "unknown"
    image[offset:offset + len(AFTER)] = AFTER
    return "patched"


def main(path):
    try:
        with open(path, "rb") as f:
            image = bytearray(f.read())
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    status = patch(image)
    if status == "patched":
        with open(path, "wb") as f:
            f.write(image)
    print(status)
    return 2 if status == "unknown" else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
