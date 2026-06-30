from __future__ import annotations

import inspect

from sirna_offtarget.pathway.evidence import runtime_v2


def test_contextual_conflict_classification_uses_typed_context_keys() -> None:
    source = inspect.getsource(runtime_v2.build_contextual_conflicts_v2)
    assert "_context_label(" not in source
    assert "_typed_context_key(" in source


def test_canonical_paths_do_not_carry_path_level_truncation() -> None:
    source = inspect.getsource(runtime_v2._trace_layer_paths)
    assert '"truncation_status"' not in source
    assert "search_result_id" in source
