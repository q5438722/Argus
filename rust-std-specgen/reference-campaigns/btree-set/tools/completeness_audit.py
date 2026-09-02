"""Independent literal reconstruction for generated completeness predicates.

This module intentionally does not import ``proof_model``.  The proof
generator and campaign checker therefore do not share a clause-translation
implementation.
"""

from __future__ import annotations

import hashlib
import json
import re

from tools import campaign_model as model


ADAPTER_PREFIXES = (
    "symmetric_difference",
    "difference",
    "intersection",
    "union",
)
OWNER_OF_PREFIX = {
    "difference": "Difference",
    "symmetric_difference": "SymmetricDifference",
    "intersection": "Intersection",
    "union": "Union",
}
OBSERVATION_PREFIXES = (
    "symmetric_difference",
    "difference",
    "intersection",
    "union",
    "range",
    "into_iter",
    "iter",
)

# Frozen source/body pair digests provide an oracle that is data-independent
# from both translation implementations. Updating a translator therefore
# requires an explicit review of every affected target instead of allowing two
# copies of the same bug to agree.
LITERAL_RECONSTRUCTION_DIGESTS = {
    "001_BTreeSet_Hash_hash_2126": "514452f489c40e25373d62ec37307ae963508047cdf25f09fbeaf65493643ff2",
    "002_BTreeSet_PartialEq_eq_2128": "b8746ffeda125cd62360685b5f3e608fa22359f20b673779d3fb8df7f88cb667",
    "003_BTreeSet_PartialOrd_partial_cmp_2131": "0466352e18045a9a284ca65308cef6ad7caf3e4dcdfe202af0362ec7855e99b7",
    "004_BTreeSet_Ord_cmp_2133": "6aafe3f40e2a20223b462368d5febd181a0ba93b992f1a8e5aa5ac9ab81dec7b",
    "005_BTreeSet_Clone_clone_2135": "39f2eafc624485d550ee6a766d5291728c5b87793b1062b083de6bfeb48201e4",
    "006_BTreeSet_Clone_clone_from_2136": "b000c64aedf08a84e0acd356af73003524816a0d6004d8bb0175e7fe4b1553e0",
    "007_Iter_Debug_fmt_2194": "13dd81c1de3cd37746c22af18e4ab1b4bbb09a37fee319182ebef5aab27585af",
    "008_IntoIter_Debug_fmt_2229": "43d58bf66d20a084decb1411fcaa729d7db205e4a4c500d599735290e7dec209",
    "009_Range_Debug_fmt_2261": "3459ea053e6486c1b038ca98c1ef1a55c25a6533f9eec397e5d08d59e8f17c21",
    "010_Difference_Debug_fmt_2294": "762bfa022b325d24bca190b0f71a6db78c0b28c797f7c2681b95cc5a8af9a8fb",
    "011_SymmetricDifference_Debug_fmt_2322": "1fa7ac25cee49311e95375b067f5dfc8641d098fd46c1ed31fee570fdbfd4308",
    "012_Intersection_Debug_fmt_2350": "570945c5a40083999984946642277a17357bbc73aad5f76171259ec3734341ab",
    "013_Union_Debug_fmt_2378": "e701418fda2c2d67528d9016cf964b5a02fb444df094c7ec325fb7d26826cf51",
    "014_BTreeSet_inherent_new_2066": "d43206022bb16d79c1c2fefde3325567fb54e622b21e03e922c6988aa07587f5",
    "015_BTreeSet_inherent_range_2069": "e7507f5c9a2aa2bd5e67d8ddebf530cbec38ae1d7c88cc1507d6d84eefafe9a1",
    "016_BTreeSet_inherent_difference_2071": "3a38fd4f6f8dfa197f0fc4a2698e65091c1b786fea96bc8138d368e452382cb6",
    "017_BTreeSet_inherent_symmetric_difference_2073": "77e2c0f66392050891be73191a1447c6a7ad32969e2be8450af4e99d5a9879cd",
    "018_BTreeSet_inherent_intersection_2075": "c6cd6092437fa1f6a96751b003b573d15552d43f2f8bbe20c72d630f3e99feee",
    "019_BTreeSet_inherent_union_2077": "f35d34b58bf72fe4e5be03b49040dbc0f6f0717e9dae6fc29ab320834421d299",
    "020_BTreeSet_inherent_clear_2079": "9309835efb0f40fc9efb63a8a5df88b7fc22987f442512db3e061b7074ef335e",
    "021_BTreeSet_inherent_contains_2080": "b2e82092e8bbf483711e0bdafe17be842ad1e4b50ecbcb81e874b308c097d9f0",
    "022_BTreeSet_inherent_get_2081": "9120d2128e35dd23d161235f46a562c9a0849f0c673af44dd7a015ed236455de",
    "023_BTreeSet_inherent_is_disjoint_2082": "4512486d49d50348079dab0574924bde15d1f035ab3555364ccd898d6da7b18d",
    "024_BTreeSet_inherent_is_subset_2083": "972de8620af10ff86ae4e19ae575881cb7ac6cbf0ea3a026e637b7977acfb029",
    "025_BTreeSet_inherent_is_superset_2084": "39bc0be8620ac95586da70c037dd4914233ade45e507f5038eb6af6972ba3cd8",
    "026_BTreeSet_inherent_first_2085": "3832237e0a19fd02d1cd34dfea2c6bbdc6d4a1fc2b5987f2ce7724ae0c652ef5",
    "027_BTreeSet_inherent_last_2086": "08a31439412887f32384275b7134baaabdf7789813f6b1ea8608faf2f794f656",
    "028_BTreeSet_inherent_pop_first_2087": "db5f166f0d62406810a86230c6d7b36b1633bf77ab0d338cfac82e74876f15c7",
    "029_BTreeSet_inherent_pop_last_2088": "fbcbd5b36a807735065f5e2b833a944e6e6baeb3cb5bc361c3a181ad0df9dd17",
    "030_BTreeSet_inherent_insert_2089": "b08a01f470be423c3895f9dfcfb7d099dce2ad2279d3b94b90aebf9729a86f31",
    "031_BTreeSet_inherent_replace_2090": "bfc0f346427e1505c86b5f8fd450066e0b7c29cd84f34a42d6a265df7c4ca2aa",
    "032_BTreeSet_inherent_remove_2093": "727685f72c2eb6c9693da191494c8de2120af3c137bdfe555a100e39dbf41eaf",
    "033_BTreeSet_inherent_take_2094": "885d93647deecd9897249963dae4701579576f2406ad90703412a5b0f2ee5d1e",
    "034_BTreeSet_inherent_retain_2095": "60f1a5fea8f842e46af9dec02e9431afc99785e1749ee65656f2a1a873a43001",
    "035_BTreeSet_inherent_append_2096": "4b1386c725c5fdb94137eaec12bcbc74823de128cd4e462c338851a3eada8d7a",
    "036_BTreeSet_inherent_split_off_2097": "5ceca6601ce4bb80bc5b3226dbb008a5aa4a284da2a37347eee5e43ef07c9d82",
    "037_BTreeSet_inherent_extract_if_2098": "659842db2bfafc2677cbac8e97b4dbad98b038eb41021813711cd9823c8ff815",
    "038_BTreeSet_inherent_iter_2064": "64c3c172490d56f34b4b2b80adb38c8caf2bb0700cd0ae8014858146db70ba94",
    "039_BTreeSet_inherent_len_2101": "2a6afa9f70e433d1141f67a8959933c01cb7476a6accd2b03d3739c5e523ff22",
    "040_BTreeSet_inherent_is_empty_2102": "2c2fec45ff70c82c6a73d8e933113ca13923de339ed912f230c75fbc87175f37",
    "041_BTreeSet_FromIterator_from_iter_2138": "d2c115e0b9eaf503fad063884f8b5c49eb312277f770dc29e7ae2bdcf75cdad1",
    "042_BTreeSet_From_from_2140": "12ebcd73a060e6d0a522e2c66cc9835bfe7437fe19fe9d7a15e41e33e91ad2cf",
    "043_BTreeSet_IntoIterator_into_iter_2065": "7b0369651620fb5d88216a67411c891d77b1aa05efab8330bc0334edc2687593",
    "044_BTreeSet_IntoIterator_into_iter_2148": "cbc1058c262a6109a0edd853e0ca1ff51550e8f3df9f6738e08e1d4f461d328b",
    "045_ExtractIf_Debug_fmt_2406": "e09cebd87d7a619c65fb1bc74ef74c62ff0957691744d9dca7aea3bfd463fb52",
    "046_ExtractIf_Iterator_next_2409": "41b16e0d555df263bb552cea08d05fc00a227851dab1ae68544ec21170087ba6",
    "047_ExtractIf_Iterator_size_hint_2410": "c93a3c595505931242c5df1939e1c138b18a1e3c0c060923ce54772fa256d16d",
    "048_BTreeSet_Extend_extend_2150": "883d7f2e03c0741717693873c0ba7f73d6c41d65d4677599b4f1c2515e6f47f5",
    "049_BTreeSet_Extend_extend_2153": "341a273a85ea8c2c443251dee0aabb514e5fde17e326534ffabf262579d610c5",
    "050_BTreeSet_Default_default_2156": "d43206022bb16d79c1c2fefde3325567fb54e622b21e03e922c6988aa07587f5",
    "051_BTreeSet_Sub_sub_2159": "420fbcfd10cc0cf8e3b0d535e4d6f7bb74a38aa4f5c9edb226774ecc648d7529",
    "052_BTreeSet_BitXor_bitxor_2163": "c1eafb3172fa30beb1cb4b97ba5f2137f7f192e18488aaf7769ec096aea3ad0d",
    "053_BTreeSet_BitAnd_bitand_2167": "c8b05c60e757210bf0b09500c40ab070c539150e9247180a09280f1f081a27dd",
    "054_BTreeSet_BitOr_bitor_2171": "fcc5ec05bd81b85afe7eda34557537329262f7c003afbf295b7fdc416359b0f7",
    "055_BTreeSet_Debug_fmt_2174": "001fc8481d8fccfe57666480974beed2b583e5f148a377583f942d7360d8174b",
    "056_Iter_Clone_clone_2196": "983d68944f3b91c0646e9b367a1133e7174e523a635ce7cf91c0dbf20841b6e8",
    "057_Iter_Iterator_next_2199": "efc8160243f5a36427dfe7aad49d1df4c67cf13dc9fe76975d36c71f4e8fd639",
    "058_Iter_Iterator_size_hint_2200": "bddf25438e4f10f73f6e7c5d4c6c0588886a8d4b37316ee42b8cbc3e943dcf9f",
    "059_Iter_Iterator_last_2201": "63ca5c9ae334b1ae13112baee8e97f83148082aa8578cca90c362cf45c4f7067",
    "060_Iter_Iterator_min_2202": "e24cae286e7b60705703e747eb3b0b9c794343cc411e8cf7c4bde4dc0a7a2356",
    "061_Iter_Iterator_max_2203": "054e6fa8a82661b71870b6054b6766a27620057587fb22d6c5757ced614a5af4",
    "062_Iter_DoubleEndedIterator_next_back_2205": "aecbcc5f665928d275f4b3ba322bd108528a4472551d6f3f0f3440382e7c00cd",
    "063_Iter_ExactSizeIterator_len_2207": "0993abbc527f64d61fe3f8609f58714924a190d4b8f3e37a7f67068b6c09b137",
    "064_IntoIter_Iterator_next_2232": "6e99b831356e93b530583b37d36eb39c2bd217fa5608b70316d7abbf615f1196",
    "065_IntoIter_Iterator_size_hint_2233": "f9cb133db3b198d0939fd11b133bfc9067062d8927c3383516c1efb09204ffe7",
    "066_Iter_Default_default_2211": "a499121e71c506ff73f8678c4bc95754fc4f764ef47af4f6549f1990bdd0b000",
    "067_IntoIter_DoubleEndedIterator_next_back_2235": "5346be5109f29bae48ac7857ab7b67a69de6b2d3e66108a5327080e7ba598802",
    "068_IntoIter_ExactSizeIterator_len_2237": "28a5bbab5bdee91499b813395607c81c28c54b047bcc1b22cfd5867c6bc40f47",
    "069_IntoIter_Default_default_2241": "7d623e6f755c67ea6ad24c3f07c6f15b752ad5548e2f5d5c627d12c8e086fc7a",
    "070_Range_Clone_clone_2263": "11ee7f101c75feddf99765e5d8523a4b6e0925ba64c106df9026c923f9bb9e29",
    "071_Range_Iterator_next_2266": "61280f86df4237147f871541687b75c3110547855989cb3d6d4161c9a448ee30",
    "072_Range_Iterator_last_2267": "288ff01d09c7c56e2746267424b1b2240c46d42b531355c40ef33a7d4a3302ed",
    "073_Range_Iterator_min_2268": "56df321cf7dd1c672829357155b651bd5356949193383ee77d1a4dcece8a9393",
    "074_Range_Iterator_max_2269": "5720affbf52ee913c1da98ca3501d5a422e7b8dfe4204d188030033c8d915752",
    "075_Range_DoubleEndedIterator_next_back_2271": "046ce2f5a1c2fc242dab4c300862666c17962c698ee9473566a12316bac3cdad",
    "076_Range_Default_default_2274": "22a0c6452f89263b3fc9039bbd33ab913ee7154fd649b7fdba845550cdba9a09",
    "077_Difference_Clone_clone_2296": "4cea88d208901630f70aa23b45b711ccd5e5033b3c335197c825743b246bf832",
    "078_Difference_Iterator_next_2299": "003f9aab4855cf4a56cd54b7c466e3512556f3224ed38e2523df536f6d14abb9",
    "079_Difference_Iterator_size_hint_2300": "aab2ba45f99cac48c522c08ed22276246f1e079de84b1442cfc93e2dc95193b0",
    "080_Difference_Iterator_min_2301": "07bba0bda07bdd7f064fce5dac30d2b8614a5f1d3474b2066f41eadda6727ba3",
    "081_SymmetricDifference_Clone_clone_2324": "60913ddf7c6722dc23c0346fc92a69f856a1c0a6fea7ffa35c11a0d121d89e79",
    "082_SymmetricDifference_Iterator_next_2327": "c22bbac5e64d4fc34e47fe23083c42d8f29e7d618df6235c2f55f84585e2415d",
    "083_SymmetricDifference_Iterator_size_hint_2328": "d1359e63978384ab6340c61c187cb00e5804fc261793fa5318d373f6d6a30b88",
    "084_SymmetricDifference_Iterator_min_2329": "47ae9387441785cde2bad4ec67e4fff16edb55ecd24ac68c42d2e2deeee2876b",
    "085_Intersection_Clone_clone_2352": "2341341b2a40e7c94d4622aa7a641ead57e78ad8f193a827d5e35dc0a9cb76ca",
    "086_Intersection_Iterator_next_2355": "a18cc54f8102768aea02405bf75d63a7a66c26ea05c7e7ee9f80cce261c83c52",
    "087_Intersection_Iterator_size_hint_2356": "2c6ff50aeeb402943f643156ac41a1be033e2241037ea1adc2e6dcc822cae92f",
    "088_Intersection_Iterator_min_2357": "3bcbe269706ea01bc5f0676c62583d6666357d6a77540e5fc03b9536c7edfadb",
    "089_Union_Clone_clone_2380": "8c346c54834df6b2290effd899407517c815f8ec74228500f6006f2dbc2c887b",
    "090_Union_Iterator_next_2383": "0e383ff0db819986114dcb1b3e067f18904cc10ffeb3e87c56446bcb5d38b721",
    "091_Union_Iterator_size_hint_2384": "8f78d2a717ad831bfcd2f2df4ab73c838f59b7be6bb2d6fbeb9792c5931eed65",
    "092_Union_Iterator_min_2385": "627638d5e2c2d0995247f855f4a7f791c97e81c68fb376dd130d1ceeb868ff8a",
}


def reconstruction_digest(
    requirements: list[str],
    clauses: list[str],
    requirement_bodies: list[str],
    clause_bodies: list[str],
) -> str:
    pairs = [
        *(
            ("require", source, body)
            for source, body in zip(
                requirements, requirement_bodies, strict=True
            )
        ),
        *(
            ("ensure", source, body)
            for source, body in zip(clauses, clause_bodies, strict=True)
        ),
    ]
    payload = json.dumps(
        pairs,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def adapter_owner_code(owner: str) -> int:
    return {
        "Difference": 1,
        "SymmetricDifference": 2,
        "Intersection": 3,
        "Union": 4,
    }[owner]


def debug_components(
    row: model.Row,
) -> tuple[str, str, str, str, str]:
    owner = row.owner["name"]
    if owner == "BTreeSet":
        return ("0", "seq![1]", "pre_seq", "Seq::empty()", "Seq::empty()")
    if owner == "Iter":
        return (
            "0",
            "seq![2, 101, 4]",
            "remaining",
            "Seq::empty()",
            "Seq::empty()",
        )
    if owner == "IntoIter":
        return (
            "0",
            "seq![3, 102, 201, 4]",
            "remaining",
            "Seq::empty()",
            "Seq::empty()",
        )
    if owner == "Range":
        return (
            "0",
            "seq![3, 103, 201, 4]",
            "remaining",
            "Seq::empty()",
            "Seq::empty()",
        )
    if owner == "Difference":
        return (
            "adapter_state.variant",
            (
                "if adapter_state.variant == 0 { "
                "seq![2, 104, 3, 110, 202, 203] "
                "} else if adapter_state.variant == 1 { "
                "seq![2, 104, 3, 111, 202, 203] "
                "} else { seq![2, 104, 2, 112] }"
            ),
            "adapter_state.first",
            (
                "if adapter_state.variant == 0 { adapter_state.second } "
                "else if adapter_state.variant == 1 { adapter_state.lookup } "
                "else { Seq::empty() }"
            ),
            "Seq::empty()",
        )
    if owner == "SymmetricDifference":
        return (
            "adapter_state.peeked_side",
            "seq![2, 105, 2, 109, 204, 205, 208]",
            "adapter_state.first",
            "adapter_state.second",
            "optional_sequence_model(adapter_state.peeked)",
        )
    if owner == "Intersection":
        return (
            "adapter_state.variant",
            (
                "if adapter_state.variant == 0 { "
                "seq![2, 106, 3, 110, 204, 205] "
                "} else if adapter_state.variant == 1 { "
                "seq![2, 106, 3, 111, 206, 207] "
                "} else { seq![2, 106, 2, 113] }"
            ),
            "adapter_state.first",
            (
                "if adapter_state.variant == 0 { adapter_state.second } "
                "else if adapter_state.variant == 1 { adapter_state.lookup } "
                "else { optional_sequence_model(adapter_state.answer) }"
            ),
            "Seq::empty()",
        )
    if owner == "Union":
        return (
            "adapter_state.peeked_side",
            "seq![2, 107, 2, 109, 204, 205, 208]",
            "adapter_state.first",
            "adapter_state.second",
            "optional_sequence_model(adapter_state.peeked)",
        )
    if owner == "ExtractIf":
        return (
            "0",
            "seq![3, 108, 208]",
            (
                "if pending.len() > 0 { seq![pending[0]] } "
                "else { Seq::empty() }"
            ),
            "Seq::empty()",
            "Seq::empty()",
        )
    raise RuntimeError(f"{row.target_id}: missing audit debug model")


def debug_law_body(row: model.Row) -> str:
    owner = row.owner["name"]
    tag = model.debug_tag(owner)
    if owner in {"Difference", "SymmetricDifference", "Intersection", "Union"}:
        state = "adapter_state"
    else:
        state = (
            "adapter_state_model(0, Seq::empty(), Seq::empty(), "
            "Seq::empty(), None, 0, None)"
        )
    return (
        f"debug_shape_law_model({tag}, {state}, pre_seq, remaining, "
        "pending)"
    )


def result_observation(row: model.Row) -> str | None:
    family = row.semantic_family
    if family == "ordered_set_comparison":
        return "comparison"
    if family == "ordered_debug_format":
        return "format_result"
    if family == "adapter_specific_size_hint":
        return None
    if family == "ordered_iterator_exact_len" or (
        family == "exact_vstd_transition"
        and row.function["name"] == "len"
    ):
        return "scalar"
    if (
        family == "exact_vstd_transition"
        and row.function["name"] == "iter"
    ):
        return "result_remaining"
    if family in {
        "set_equality",
        "set_relation_observer",
        "ordered_endpoint_observer",
        "ordered_endpoint_removal",
        "representative_replacement",
        "borrowed_representative_removal",
        "ordered_iterator_forward_step",
        "ordered_iterator_backward_step",
        "ordered_iterator_terminal_selection",
    } or (
        family == "exact_vstd_transition"
        and row.function["name"] in {
            "contains",
            "get",
            "insert",
            "remove",
            "is_empty",
        }
    ):
        return "returned"
    return None


def observation_substitutions(
    row: model.Row,
) -> list[tuple[str, str]]:
    owner = row.owner["name"]
    substitutions: list[tuple[str, str]] = []
    if row.semantic_family == "ordered_set_hash":
        substitutions.extend(
            (
                ("*final(state)", "post_hasher"),
                ("*old(state)", "pre_hasher"),
            )
        )
    if row.semantic_family == "ordered_debug_format":
        tag = model.debug_tag(owner)
        variant, structure, primary, secondary, tertiary = debug_components(row)
        non_exhaustive = "true" if owner == "ExtractIf" else "false"
        shape = (
            f"{tag}, {variant}, {structure}, {primary}, {secondary}, "
            f"{tertiary}, {non_exhaustive}"
        )
        prefix = {
            "BTreeSet": "btree_set",
            "Iter": "iter",
            "IntoIter": "into_iter",
            "Range": "range",
            "Difference": "difference",
            "SymmetricDifference": "symmetric_difference",
            "Intersection": "intersection",
            "Union": "union",
            "ExtractIf": "extract_if",
        }[owner]
        substitutions.extend(
            (
                (
                    f"*final(f) == apply_debug_shape("
                    f"*old(f), {prefix}_debug_shape(*this)).0",
                    f"post_formatter == debug_shape_state_model("
                    f"pre_formatter, {shape})",
                ),
                (
                    f"result == apply_debug_shape("
                    f"*old(f), {prefix}_debug_shape(*this)).1",
                    f"format_result == debug_shape_result_model("
                    f"pre_formatter, {shape})",
                ),
                (
                    f"{prefix}_debug_shape_law(*this)",
                    debug_law_body(row),
                ),
            )
        )
    substitutions.extend(
        (
            ("btree_set_sequence(result)", "result_seq"),
            ("result@", "result_set"),
            ("btree_set_sequence(*source)", "other_seq"),
            ("source@", "other_set"),
            ("btree_set_sequence(*old(other))", "other_seq"),
            ("btree_set_sequence(*final(other))", "other_post_seq"),
            ("final(other)@", "other_post_set"),
            ("old(other)@", "other_set"),
            ("rhs@", "other_set"),
        )
    )
    if row.semantic_family == "extract_if_construction":
        substitutions.extend(
            (
                ("extract_if_set(result)", "iterator_set"),
                ("extract_if_pending(result)", "result_pending"),
                ("extract_if_callback_count(result)", "result_callback_count"),
                ("extract_if_predicate_state(result)", "result_predicate_state"),
                ("extract_if_remaining(result)", "result_remaining"),
                ("extract_if_initial_set(result)", "result_initial_set"),
                ("extract_if_yielded(result)", "result_yielded"),
                (
                    "extract_if_drop_law(result)",
                    "drop_set == partial_drop_set_model("
                    "result_initial_set, result_yielded)",
                ),
                (
                    "extract_if_panic_law(result)",
                    "panic_set == iterator_set",
                ),
            )
        )
    if owner == "ExtractIf" and row.function["name"] == "next":
        substitutions.extend(
            (
                ("extract_if_pending(*final(this))", "post_pending"),
                ("extract_if_pending(*old(this))", "pending"),
                ("extract_if_set(*final(this))", "post_set"),
                ("extract_if_set(*old(this))", "pre_set"),
                (
                    "extract_if_callback_count(*final(this))",
                    "post_callback_count",
                ),
                (
                    "extract_if_callback_count(*old(this))",
                    "pre_callback_count",
                ),
                (
                    "extract_if_predicate_state(*final(this))",
                    "post_predicate_state",
                ),
                (
                    "extract_if_predicate_state(*old(this))",
                    "predicate_state",
                ),
                (
                    "extract_if_initial_set(*final(this))",
                    "post_initial_set",
                ),
                (
                    "extract_if_initial_set(*old(this))",
                    "extract_initial_set",
                ),
                ("extract_if_yielded(*final(this))", "post_yielded"),
                ("extract_if_yielded(*old(this))", "yielded"),
                ("extract_if_remaining(*final(this))", "post_remaining"),
                ("extract_if_remaining(*old(this))", "remaining"),
                (
                    "extract_if_drop_law(*final(this))",
                    "drop_set == partial_drop_set_model("
                    "post_initial_set, post_yielded)",
                ),
                (
                    "extract_if_panic_law(*final(this))",
                    "panic_set == post_set",
                ),
            )
        )
    if (
        row.semantic_family == "exact_vstd_transition"
        and row.function["name"] == "iter"
    ):
        substitutions.extend(
            (
                ("spec_btree_keys_iter(this)", "pre_seq"),
                ("IteratorSpec::decrease(&result) is Some", "decrease_defined"),
                (
                    "IteratorSpec::initial_value_relation(&result, &result)",
                    "initial_relation",
                ),
            )
        )
    if row.semantic_family == "exact_vstd_transition":
        substitutions.append(("spec_btree_set_len(this)", "pre_set.len()"))
    for prefix in OBSERVATION_PREFIXES:
        substitutions.extend(
            (
                (f"{prefix}_remaining(this)", "remaining"),
                (f"{prefix}_remaining(&this)", "remaining"),
            )
        )
    if row.semantic_family == "adapter_specific_size_hint":
        if owner in {"Difference", "Intersection"}:
            second = (
                "if adapter_state.variant == 0 { "
                "adapter_state.second.len() } "
                "else if adapter_state.variant == 1 { "
                "adapter_state.lookup.len() } else { 0 }"
            )
            lengths = f"(adapter_state.first.len(), {second})"
        elif owner in {"SymmetricDifference", "Union"}:
            lengths = (
                "(adapter_merge_left_model(adapter_state).len(), "
                "adapter_merge_right_model(adapter_state).len())"
            )
        else:
            lengths = ""
        if lengths:
            prefix = {
                "Difference": "difference",
                "SymmetricDifference": "symmetric_difference",
                "Intersection": "intersection",
                "Union": "union",
            }[owner]
            substitutions.append((f"{prefix}_hint_lengths(this)", lengths))
    return substitutions


def generic_substitutions(row: model.Row) -> list[tuple[str, str]]:
    substitutions = [
        ("(obeys_cmp::<T>() && K::obeys_cmp_spec())", "order_laws"),
        ("(obeys_cmp::<T>() && Q::obeys_cmp_spec())", "order_laws"),
        ("(obeys_cmp::<T>())", "order_laws"),
        ("(T::obeys_partial_cmp_spec())", "order_laws"),
        ("Some(upper) =>", "Some(value) =>"),
        ("upper as nat", "value"),
    ]
    for prefix in ADAPTER_PREFIXES:
        code = adapter_owner_code(OWNER_OF_PREFIX[prefix])
        substitutions.extend(
            (
                (
                    f"{prefix}_source_state_law(result)",
                    f"adapter_state_law_model({code}, "
                    "result_adapter_state, result_remaining)",
                ),
                (
                    f"{prefix}_source_state_law(*final(this))",
                    f"adapter_state_law_model({code}, "
                    "post_adapter_state, post_remaining)",
                ),
                (
                    f"{prefix}_source_state_law(*old(this))",
                    f"adapter_state_law_model({code}, "
                    "adapter_state, remaining)",
                ),
                (
                    f"{prefix}_source_state_law(*this)",
                    f"adapter_state_law_model({code}, "
                    "adapter_state, remaining)",
                ),
                (f"{prefix}_hint_variant(this)", "adapter_state.variant"),
            )
        )
    for prefix in OBSERVATION_PREFIXES:
        substitutions.extend(
            (
                (f"{prefix}_remaining(result).unref()", "result_remaining"),
                (f"{prefix}_remaining(result)", "result_remaining"),
                (f"{prefix}_remaining(*final(this))", "post_remaining"),
                (f"{prefix}_remaining(*old(this))", "remaining"),
                (f"{prefix}_remaining(*this)", "remaining"),
                (f"{prefix}_source_state(result)", "result_adapter_state"),
                (f"{prefix}_source_state(*final(this))", "post_adapter_state"),
                (f"{prefix}_source_state(*old(this))", "adapter_state"),
                (f"{prefix}_source_state(*this)", "adapter_state"),
            )
        )
    substitutions.extend(
        (
            (
                "extract_if_decisions(result)",
                "callback_decisions_model(predicate_seed, result_pending)",
            ),
            (
                "extract_if_decisions(*old(this))",
                "callback_decisions_model(predicate_state, pending)",
            ),
            ("extract_if_pending(result)", "result_pending"),
            ("extract_if_pending(*old(this))", "pending"),
            ("extract_if_pending(*this)", "pending"),
            ("extract_if_remaining(*this)", "remaining"),
            ("extract_if_predicate_state(*this)", "predicate_state"),
            ("extract_if_length_bound(this)", "pre_set.len()"),
            ("into_iterator_sequence::<T, I>(&iter)", "input_seq"),
            ("arr@", "input_seq"),
            (
                "range_bounds_law(&range)",
                "range_bounds_model_law(range_start_kind, range_end_kind)",
            ),
            (
                "range_start_after_end(&range)",
                "range_start_after_end_model(range_start_kind, "
                "range_start_value, range_end_kind, range_end_value)",
            ),
            (
                "range_equal_excluded(&range)",
                "range_equal_excluded_model(range_start_kind, "
                "range_start_value, range_end_kind, range_end_value)",
            ),
            ("btree_set_sequence(*old(this))", "pre_seq"),
            ("btree_set_sequence(*final(this))", "post_seq"),
            ("btree_set_sequence(*this)", "pre_seq"),
            ("btree_set_sequence(this)", "pre_seq"),
            ("btree_set_sequence(*other)", "other_seq"),
            ("btree_set_sequence(*rhs)", "other_seq"),
            ("final(this)@", "post_set"),
            ("old(this)@", "pre_set"),
            ("this@", "pre_set"),
            ("other@", "other_set"),
            (
                "range_order_law(pre_seq, &range)",
                "range_bounds_model_law(range_start_kind, range_end_kind)",
            ),
            ("result.0 as nat", "lower"),
            ("result.0", "lower"),
            ("result.1", "upper"),
            ("increasing_seq(", "strictly_increasing_model("),
            ("nondecreasing_sequence(", "nondecreasing_model("),
            ("stable_tie_order(", "stable_tie_order_model("),
            ("stable_sorted_sequence(", "stable_sorted_sequence_model("),
            (
                "difference_sequence(pre_seq, other_seq)",
                "difference_sequence_model(pre_seq, other_seq)",
            ),
            (
                "symmetric_difference_sequence(pre_seq, other_seq)",
                "symmetric_difference_sequence_model(pre_seq, other_seq)",
            ),
            (
                "intersection_source_sequence(pre_seq, other_seq)",
                "intersection_sequence_model(pre_seq, other_seq)",
            ),
            (
                "union_sequence(pre_seq, other_seq)",
                "union_sequence_model(pre_seq, other_seq)",
            ),
            ("obeys_cmp::<T>()", "order_laws"),
            ("key_obeys_cmp_spec::<T>()", "order_laws"),
            ("K::obeys_cmp_spec()", "order_laws"),
            ("Q::obeys_cmp_spec()", "order_laws"),
            ("T::obeys_cmp_spec()", "order_laws"),
            ("T::obeys_partial_cmp_spec()", "order_laws"),
        )
    )
    return substitutions


def reconstruct(row: model.Row, source: str) -> str:
    text = source
    if "match result { Some(item) =>" in text:
        text = text.replace(
            "match result { Some(item) =>",
            "match result { Some(found) =>",
        ).replace("&item", "found").replace("*item", "found")
    text = re.sub(
        r"retain_decisions\(&f, ([^)]*)\)",
        r"callback_decisions_model(predicate_seed, \1)",
        text,
    )
    text = re.sub(
        r"retain_effect_trace\(&f, ([^)]*)\)",
        r"callback_states_model(predicate_seed, \1)",
        text,
    )
    text = re.sub(
        r"retain_callback_trace_law\(f, ([^)]*)\)",
        r"callback_trace_law_model(predicate_seed, \1)",
        text,
    )
    text = text.replace(
        "retain_callback_trace_law(",
        "callback_trace_law_model(",
    ).replace(
        "borrowed_key_order_law(",
        "borrowed_key_order_law_model(",
    )
    for old, new in observation_substitutions(row):
        text = text.replace(old, new)
    text = re.sub(r"\bvalue\b", "item", text)
    for old, new in generic_substitutions(row):
        text = text.replace(old, new)
    text = re.sub(
        r"into_iterator_sequence::<[^>]+>\(&iter\)(?:\.unref\(\))?",
        "input_seq",
        text,
    )
    for old, new in (
        ("apply_set_hash", "apply_set_hash_model"),
        ("seq_eq_spec", "sequence_equal_model"),
        ("seq_lex_partial_cmp", "sequence_partial_compare_model"),
        ("seq_lex_cmp", "lex_compare_model"),
        ("clone_sequence_preserves_values", "clone_sequence_preserves_values_model"),
        ("clone_sequence", "clone_sequence_model"),
        ("dedup_last_sorted", "dedup_last_sorted_model"),
        ("extend_sequence", "extend_sequence_model"),
        ("retain_selected", "retain_selected_model"),
        ("first_true", "first_true_model"),
        ("retain_callback_state_after", "callback_state_after_model"),
        ("sets_borrowed_key_to_key", "borrowed_key_represents_model"),
        ("sets_differ_by_borrowed_key", "borrowed_set_difference_model"),
        ("set_contains_borrowed_key", "borrowed_set_contains_model"),
        ("replace_representative", "replace_representative_model"),
        ("cmp_equal_representative", "representative_model"),
        ("borrowed_representative", "representative_model"),
        ("remove_borrowed_representative", "remove_representative_model"),
        ("difference_initial_state", "difference_initial_state_model"),
        ("intersection_initial_state", "intersection_initial_state_model"),
        ("merge_initial_state", "merge_initial_state_model"),
        ("intersection_hint_lower", "intersection_hint_lower_model"),
        ("intersection_hint_upper", "intersection_hint_upper_model"),
        ("difference_next_step", "difference_next_step_model"),
        (
            "symmetric_difference_next_step",
            "symmetric_difference_next_step_model",
        ),
        ("intersection_next_step", "intersection_next_step_model"),
        ("union_next_step", "union_next_step_model"),
    ):
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    bounds = (
        "range_start_kind, range_start_value, "
        "range_end_kind, range_end_value"
    )
    text = text.replace("&range", bounds)
    text = text.replace("range_sequence(", "range_sequence_model(")
    text = text.replace("split_before(", "split_before_model(")
    text = text.replace("split_at_or_after(", "split_at_or_after_model(")
    text = text.replace("old(other)@", "other_set")
    text = text.replace("rhs@", "other_set")
    text = text.replace("obeys_cmp::<&'a T>()", "order_laws")
    if row.semantic_family == "extract_if_construction":
        text = re.sub(r"\bpred\b", "predicate_seed", text)
    result = result_observation(row)
    if result is not None:
        text = re.sub(r"\bresult\b", result, text)
    return text


def reconstruct_clause(row: model.Row, source: str) -> str:
    body = reconstruct(row, source)
    needs_order_laws = (
        model.comparison_law_binding(row) is not None
        or (
            row.semantic_family == "exact_vstd_transition"
            and row.function["name"] in {
                "contains",
                "get",
                "insert",
                "remove",
                "iter",
            }
        )
    )
    if needs_order_laws and not body.startswith("order_laws ==>"):
        return f"order_laws ==> ({body})"
    return body
