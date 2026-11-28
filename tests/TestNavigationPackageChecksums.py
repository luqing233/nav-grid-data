"""Validate the published navigation package against its checked-out files."""
import hashlib
import json
import unittest
from pathlib import Path


class TestNavigationPackageChecksums(unittest.TestCase):
    def test_package_hashes_match_files(self):
        root = Path(__file__).resolve().parents[1] / "navigation"
        package = json.loads((root / "prepared-package.json").read_text(encoding="utf-8"))
        files = {
            "dataset_sha256": root / "dataset.json",
            "localization_manifest_sha256": root / "localization" / "manifest.json",
            "prepared_manifest_sha256": root / "localization" / "prepared" / "manifest.json",
        }
        for key, path in files.items():
            with self.subTest(file=str(path), checksum=key):
                self.assertEqual(package[key], hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
