from __future__ import annotations

from dataclasses import replace

from sirna_offtarget.expression.contracts_v2 import NormalizedGeneEffectRecordV2
from sirna_offtarget.expression.downstream import normalized_gene_effect_v2_to_downstream_view
from tests.unit.expression.artifacts.test_committed_loader_safety import _v2_record


def test_downstream_counts_reconcile_with_v2_records() -> None:
    records = [
        NormalizedGeneEffectRecordV2(**_v2_record()),
        replace(
            NormalizedGeneEffectRecordV2(**_v2_record()),
            record_id="r2",
            canonical_gene_id=None,
        ),
    ]
    view = normalized_gene_effect_v2_to_downstream_view(records)

    assert len(records) == len(view.records) + len(view.exclusions)
