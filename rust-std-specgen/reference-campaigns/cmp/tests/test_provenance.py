from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import provenance


class ProvenanceUtilityTests(unittest.TestCase):
    def test_metadata_fingerprint_detects_same_size_file_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            payload = root / "payload.bin"
            payload.write_bytes(b"abc")
            before = provenance.metadata_tree_fingerprint(root)

            original_stat = payload.stat()
            payload.write_bytes(b"xyz")
            os.utime(
                payload,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 1_000_000),
            )
            after = provenance.metadata_tree_fingerprint(root)

            self.assertEqual(before["content_bytes_read"], 0)
            self.assertEqual(before["total_regular_bytes"], after["total_regular_bytes"])
            self.assertNotEqual(before["metadata_sha256"], after["metadata_sha256"])

    def test_metadata_fingerprint_accounts_for_symlinks_without_following(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.write_bytes(b"payload")
            (root / "link").symlink_to("target")

            fingerprint = provenance.metadata_tree_fingerprint(root)

            self.assertEqual(fingerprint["entry_type_counts"]["regular"], 1)
            self.assertEqual(fingerprint["entry_type_counts"]["symlink"], 1)
            self.assertEqual(fingerprint["total_regular_bytes"], len(b"payload"))

    def test_source_manifest_csv_is_deterministic(self) -> None:
        record = {field: f"value-{field}" for field in provenance.SOURCE_CSV_FIELDS}

        first = provenance.source_manifest_csv([record])
        second = provenance.source_manifest_csv([record])

        self.assertEqual(first, second)
        self.assertTrue(first.startswith(b"identifier,role,source_root,"))

    def test_static_manifest_contract_rejects_tampering(self) -> None:
        manifest = {
            "schema_version": provenance.SCHEMA_VERSION,
            "campaign": provenance.expected_campaign_record(),
            "commands": provenance.expected_command_records(),
            "hash_algorithm": "sha256",
        }
        source_manifest = {
            "schema_version": provenance.SCHEMA_VERSION,
            "module": provenance.CAMPAIGN_MODULE,
            "rust_release": provenance.RUST_RELEASE,
        }
        preservation = {
            "schema_version": provenance.SCHEMA_VERSION,
            "policy": provenance.PRESERVATION_POLICY,
        }
        provenance.validate_static_manifest_contract(
            manifest,
            source_manifest,
            preservation,
        )

        mutations = (
            ("campaign scope", manifest, ("campaign", "scope"), "wrong scope"),
            (
                "capture command",
                manifest,
                ("commands", "capture", "command"),
                "python3 wrong.py",
            ),
            (
                "source Rust release",
                source_manifest,
                ("rust_release",),
                "1.95.0",
            ),
            (
                "preservation policy",
                preservation,
                ("policy", "negative_lessons_workspace"),
                "read protected contents",
            ),
        )
        for label, original, path, replacement in mutations:
            with self.subTest(label=label):
                changed_manifest = copy.deepcopy(manifest)
                changed_source = copy.deepcopy(source_manifest)
                changed_preservation = copy.deepcopy(preservation)
                changed_objects = {
                    id(manifest): changed_manifest,
                    id(source_manifest): changed_source,
                    id(preservation): changed_preservation,
                }
                target = changed_objects[id(original)]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.validate_static_manifest_contract(
                        changed_manifest,
                        changed_source,
                        changed_preservation,
                    )

    def test_source_snapshot_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.rs"
            snapshot = root / "provenance/snapshots/rust/source.rs"
            source.write_bytes(b"abc")
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b"abc")
            source_input = provenance.SourceInput(
                "test_source",
                "negative_test",
                "rust",
                source,
                "source.rs",
                "provenance/snapshots/rust/source.rs",
            )
            captured_at = "2026-08-28T00:00:00Z"
            with (
                mock.patch.object(provenance, "CAMPAIGN_ROOT", root),
                mock.patch.object(provenance, "SOURCE_INPUTS", (source_input,)),
            ):
                expected_records = provenance.source_records(
                    captured_at,
                    write_snapshots=False,
                )
                source_manifest = {
                    "captured_at_utc": captured_at,
                    "record_count": 1,
                    "records": expected_records,
                }
                snapshot.write_bytes(b"xyz")
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.validate_source_records(source_manifest)

    def test_refresh_preserves_unchanged_snapshot_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.rs"
            snapshot = root / "provenance/snapshots/rust/source.rs"
            source.write_bytes(b"unchanged")
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b"unchanged")
            original_timestamp = snapshot.stat().st_mtime_ns
            source_input = provenance.SourceInput(
                "test_source",
                "negative_test",
                "rust",
                source,
                "source.rs",
                "provenance/snapshots/rust/source.rs",
            )

            with (
                mock.patch.object(provenance, "CAMPAIGN_ROOT", root),
                mock.patch.object(provenance, "SOURCE_INPUTS", (source_input,)),
            ):
                provenance.source_records(
                    "2026-08-31T00:00:00Z",
                    write_snapshots=True,
                )

            self.assertEqual(snapshot.stat().st_mtime_ns, original_timestamp)

    def test_source_set_is_unique_and_cmp_scoped(self) -> None:
        identifiers = [item.identifier for item in provenance.SOURCE_INPUTS]
        snapshot_paths = [item.snapshot_relpath for item in provenance.SOURCE_INPUTS]

        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(len(snapshot_paths), len(set(snapshot_paths)))
        self.assertTrue(any(path.endswith("/core/src/cmp.rs") for path in snapshot_paths))
        self.assertTrue(
            any(path.endswith("/vstd/std_specs/cmp.rs") for path in snapshot_paths)
        )
        self.assertFalse(any("result" in path.lower() for path in snapshot_paths))
        self.assertFalse(any("btreemap" in path.lower() for path in snapshot_paths))
        self.assertFalse(any("btreeset" in path.lower() for path in snapshot_paths))

    def test_rustdoc_commands_are_campaign_local_and_rust_1_96(self) -> None:
        contracts = provenance.rustdoc_command_contract()

        self.assertEqual(set(contracts), {"clean", "rustdoc"})
        for contract in contracts.values():
            self.assertIn("+1.96.0", contract["argv"])
            self.assertEqual(
                contract["working_directory"],
                str(provenance.CAMPAIGN_ROOT),
            )
        self.assertIn(str(provenance.RUSTDOC_TARGET), contracts["clean"]["argv"])
        self.assertEqual(
            contracts["rustdoc"]["environment_overrides"]["CARGO_TARGET_DIR"],
            str(provenance.RUSTDOC_TARGET),
        )


if __name__ == "__main__":
    unittest.main()
