from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_expression_normalization_docs_exist_before_boundary_code() -> None:
    assert (ROOT / "docs/algorithm_comparison/expression_normalization_comparison.md").exists()
    assert (ROOT / "docs/algorithm_comparison/expression_normalization_decision.md").exists()
    assert (ROOT / "docs/algorithm_comparison/expression_normalization_limitations.md").exists()
    assert (
        ROOT / "docs/algorithm_recovery/expression_normalization_original_requirements.md"
    ).exists()


def test_expression_contract_modules_do_not_import_pathway_mechanistic_layers() -> None:
    for relative in (
        "src/sirna_offtarget/expression/contracts.py",
        "src/sirna_offtarget/expression/committed.py",
        "src/sirna_offtarget/expression/validation.py",
    ):
        tree = ast.parse((ROOT / relative).read_text())
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        assert not any(module.startswith("sirna_offtarget.pathway") for module in imports)
        removed_package = ".".join(("sirna_offtarget", "scoring"))
        assert not any(module.startswith(removed_package) for module in imports)
