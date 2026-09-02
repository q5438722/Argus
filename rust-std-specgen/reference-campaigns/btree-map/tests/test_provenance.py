from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_provenance


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = verify_provenance.load_manifest()

    def test_live_provenance_is_valid(self) -> None:
        self.assertEqual(
            verify_provenance.verify_manifest(self.manifest, ROOT),
            [],
        )

    def test_scope_is_btree_map_only(self) -> None:
        self.assertEqual(self.manifest["module"], "alloc::collections::btree_map")
        ownership = self.manifest["ownership"]
        self.assertEqual(
            ownership["inventory_status"],
            "complete_151_stable_executable_rows",
        )
        self.assertEqual(
            ownership["exact_vstd_match_status"],
            "complete_13_exact_vstd_rows",
        )
        self.assertIn("alloc::collections::btree_set", ownership["excluded_modules"])

    def test_vstd_and_cmp_are_reference_only(self) -> None:
        artifacts = {item["id"]: item for item in self.manifest["artifacts"]}
        for artifact_id in ("vstd_btree", "vstd_cmp", "vstd_laws_cmp"):
            self.assertIsNone(artifacts[artifact_id]["frozen_path"])
            self.assertTrue(
                artifacts[artifact_id]["scope_treatment"].startswith(
                    "hash_reference_only"
                )
            )

    def test_verus_embeds_rust_1_96(self) -> None:
        verus = next(tool for tool in self.manifest["tools"] if tool["id"] == "verus")
        self.assertIn(
            "  Toolchain: 1.96.0-x86_64-unknown-linux-gnu",
            verus["version_stdout"],
        )
        ambient = self.manifest["observed_non_authoritative_tools"][0]
        self.assertFalse(ambient["use_for_campaign_evidence"])


if __name__ == "__main__":
    unittest.main()
