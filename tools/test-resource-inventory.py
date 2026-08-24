#!/usr/bin/env python3
"""Focused regression tests for historical Git and Git LFS provenance."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("resource_inventory", Path(__file__).with_name("resource-inventory.py"))
assert SPEC is not None and SPEC.loader is not None
resource_inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resource_inventory)


class ResourceInventoryTests(unittest.TestCase):
    def test_lfs_pointer_parser_returns_payload_identity(self) -> None:
        oid = "a" * 64
        self.assertEqual(
            resource_inventory.parse_lfs_pointer(
                (
                    f"{resource_inventory.LFS_POINTER_VERSION}\n"
                    f"oid sha256:{oid}\n"
                    "size 12\n"
                ).encode("ascii")
            ),
            (oid, 12),
        )

    def test_lfs_pointer_parser_rejects_malformed_size(self) -> None:
        with self.assertRaisesRegex(resource_inventory.InventoryError, "pointer size"):
            resource_inventory.parse_lfs_pointer(
                (
                    f"{resource_inventory.LFS_POINTER_VERSION}\n"
                    f"oid sha256:{'a' * 64}\n"
                    "size twelve\n"
                ).encode("ascii")
            )

    def test_git_bytes_hydrates_a_tracked_lfs_asset(self) -> None:
        expected = (ROOT / "paintings" / "canopy.jpg").read_bytes()
        actual = resource_inventory.git_bytes(ROOT, "HEAD", "paintings/canopy.jpg")
        self.assertEqual(actual, expected)

    def test_missing_history_reports_revision_and_path(self) -> None:
        revision = "0" * 40
        with self.assertRaisesRegex(
            resource_inventory.InventoryError,
            rf"{revision}:paintings/canopy.png",
        ):
            resource_inventory.git_bytes(ROOT, revision, "paintings/canopy.png")

    def test_catalog_provenance_coordinates_are_readable(self) -> None:
        catalog = json.loads((ROOT / "catalog" / "resources.json").read_text(encoding="utf-8"))
        resource_inventory.validate_catalog_provenance(ROOT, catalog)


if __name__ == "__main__":
    unittest.main(verbosity=2)
