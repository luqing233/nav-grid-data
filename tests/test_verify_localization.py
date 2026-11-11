"""Header parsing stays dependency-free; fixtures contain complete encoded images."""
import base64
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_localization", ROOT / "scripts/verify_localization.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ImageHeaderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "image"
        self.fixtures = json.loads((ROOT / "tests/image-fixtures.json").read_text())

    def test_png_and_all_three_webp_headers(self):
        for name, encoded in self.fixtures.items():
            with self.subTest(name=name):
                self.path.write_bytes(base64.b64decode(encoded))
                self.assertEqual(VERIFY.image_size(self.path), (7, 5))

    def test_truncated_webp_is_rejected(self):
        for name, encoded in self.fixtures.items():
            if name == "png":
                continue
            with self.subTest(name=name):
                self.path.write_bytes(base64.b64decode(encoded)[:-3])
                with self.assertRaises(ValueError):
                    VERIFY.image_size(self.path)

    def test_invalid_chunk_size_is_rejected(self):
        raw = bytearray(base64.b64decode(self.fixtures["vp8"]))
        raw[16:20] = struct.pack("<I", 0xffffffff)
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):
            VERIFY.image_size(self.path)

    def test_pointer_and_unknown_content_are_rejected(self):
        for raw in (b"version https://git-lfs.github.com/spec/v1\n", b"", b"not an image"):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError):
                VERIFY.image_size(self.path)


if __name__ == "__main__":
    unittest.main()
