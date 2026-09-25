"""Run: python3 -m unittest discover tests"""
import os
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from patch_libcef import AFTER, BEFORE, RVA, patch  # noqa: E402
SECTION_RVA = 0x1000
SECTION_RAW = 0x400


def fake_pe(code_at_rva: bytes) -> bytearray:
    """Minimal PE: one section mapping RVA 0x1000 to file offset 0x400, `code_at_rva` placed at RVA."""
    pe_offset = 0x80
    optional_header_size = 0xE0
    size = SECTION_RAW + (RVA - SECTION_RVA) + 0x100
    image = bytearray(size)
    struct.pack_into("<I", image, 0x3C, pe_offset)
    image[pe_offset:pe_offset + 4] = b"PE\0\0"
    struct.pack_into("<H", image, pe_offset + 6, 1)  # NumberOfSections
    struct.pack_into("<H", image, pe_offset + 20, optional_header_size)
    section = pe_offset + 24 + optional_header_size
    image[section:section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", image, section + 8, size, SECTION_RVA, size - SECTION_RAW, SECTION_RAW)
    offset = SECTION_RAW + RVA - SECTION_RVA
    image[offset:offset + len(code_at_rva)] = code_at_rva
    return image


class PatchTest(unittest.TestCase):
    def test_patches_the_known_build(self):
        image = fake_pe(BEFORE)
        self.assertEqual(patch(image), "patched")
        offset = SECTION_RAW + RVA - SECTION_RVA
        self.assertEqual(bytes(image[offset:offset + len(AFTER)]), AFTER)

    def test_is_idempotent(self):
        image = fake_pe(BEFORE)
        patch(image)
        once = bytes(image)
        self.assertEqual(patch(image), "already")
        self.assertEqual(bytes(image), once)

    def test_leaves_an_unknown_build_untouched(self):
        image = fake_pe(b"\x90" * len(BEFORE))
        original = bytes(image)
        self.assertEqual(patch(image), "unknown")
        self.assertEqual(bytes(image), original)

    def test_rejects_a_file_that_is_not_a_pe(self):
        self.assertEqual(patch(bytearray(b"MZ" + b"\0" * 10)), "unknown")
        self.assertEqual(patch(bytearray()), "unknown")

    def test_rva_outside_every_section(self):
        image = fake_pe(BEFORE)
        del image[SECTION_RAW:]  # section table still claims data that is gone
        self.assertEqual(patch(image), "unknown")

    def test_cli_writes_file_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            dll = os.path.join(tmp, "libcef.dll")
            with open(dll, "wb") as f:
                f.write(fake_pe(BEFORE))
            run = lambda: subprocess.run([sys.executable, os.path.join(ROOT, "patch_libcef.py"), dll],
                                         capture_output=True, text=True)
            first, second = run(), run()
            self.assertEqual((first.returncode, first.stdout.strip()), (0, "patched"))
            self.assertEqual((second.returncode, second.stdout.strip()), (0, "already"))
            with open(dll, "wb") as f:
                f.write(fake_pe(b"\x90" * len(BEFORE)))
            self.assertEqual(run().returncode, 2)
            missing = subprocess.run([sys.executable, os.path.join(ROOT, "patch_libcef.py"),
                                      os.path.join(tmp, "nope.dll")], capture_output=True, text=True)
            self.assertEqual(missing.returncode, 1)


if __name__ == "__main__":
    unittest.main()
