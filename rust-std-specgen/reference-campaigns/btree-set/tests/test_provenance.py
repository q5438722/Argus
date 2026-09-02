from __future__ import annotations

import unittest
from pathlib import Path

from tools.check_provenance import validate
from tools.provenance_common import INPUTS


CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]


class ProvenanceTests(unittest.TestCase):
    def test_frozen_inputs_match_live_authorities(self) -> None:
        summary = validate(CAMPAIGN_ROOT)
        self.assertEqual(summary["inputs"], len(INPUTS))
        self.assertGreater(summary["frozen_bytes"], 0)
        self.assertGreater(summary["rustdoc_items"], 0)

    def test_freeze_policy_is_unique_and_module_scoped(self) -> None:
        source_paths = [item.source_path for item in INPUTS]
        frozen_paths = [item.frozen_path for item in INPUTS]
        self.assertEqual(len(source_paths), len(set(source_paths)))
        self.assertEqual(len(frozen_paths), len(set(frozen_paths)))
        self.assertTrue(
            all(
                path.startswith(("rust-1.96/", "verus/", "rustdoc-json-1.96/"))
                for path in source_paths
            )
        )
        self.assertFalse(any("vec_deque" in path or "hash_set" in path for path in source_paths))


if __name__ == "__main__":
    unittest.main()
