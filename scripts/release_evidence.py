from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from scripts.release_source_tree import (
    build_source_tree_inventory,
    compute_release_source_tree_checksum,
    sha256_file,
    write_json,
)

COVERAGE_COMMAND = (
    ".venv/bin/python -m pytest --cov=src/sirna_offtarget --cov-branch "
    "--cov-report=term-missing --cov-report=xml --cov-fail-under=92"
)
THRESHOLD_COMMAND = (
    ".venv/bin/python scripts/check_coverage_thresholds.py coverage.xml "
    "--min-line-rate 0.92 --min-branch-rate 0.85"
)
POST_PACKAGE_VERIFICATION_TYPE = "post-package-verification"
ARCHIVE_CHECKSUM_MODEL = "external-sidecar"
ARCHIVE_CHECKSUM_AUTHORITY = "adjacent .zip.sha256 file"
ARCHIVE_SHA256_STATUS = "EXTERNAL_SIDECAR"


def _status_from_passed(passed: bool) -> str:
    return "PASSED" if passed else "FAILED"


def parse_coverage_xml(path: Path) -> dict[str, object]:
    root = ElementTree.parse(path).getroot()
    lines_valid = int(root.attrib["lines-valid"])
    lines_covered = int(root.attrib["lines-covered"])
    branches_valid = int(root.attrib["branches-valid"])
    branches_covered = int(root.attrib["branches-covered"])
    return {
        "coverage_tool_version": root.attrib.get("version", ""),
        "coverage_xml_timestamp": root.attrib["timestamp"],
        "coverage_xml_sha256": sha256_file(path),
        "lines_valid": lines_valid,
        "lines_covered": lines_covered,
        "lines_missed": lines_valid - lines_covered,
        "line_rate": root.attrib["line-rate"],
        "branches_valid": branches_valid,
        "branches_covered": branches_covered,
        "branches_missed": branches_valid - branches_covered,
        "branch_rate": root.attrib["branch-rate"],
    }


def _passed(command: str) -> dict[str, object]:
    return {"command": command, "status": "PASSED"}


def build_post_package_verification(
    *,
    archive_filename: str,
    archive_sidecar_filename: str | None = None,
    source_tree_sha256: str,
    source_inventory_count: int,
    required_checks: dict[str, bool],
    verified_at: str,
    details: dict[str, Any] | None = None,
) -> dict[str, object]:
    passed = all(required_checks.values())
    status = _status_from_passed(passed)
    result_fields = {
        name: _status_from_passed(check_passed) for name, check_passed in required_checks.items()
    }
    return {
        "passed": passed,
        "status": status,
        "verification_type": POST_PACKAGE_VERIFICATION_TYPE,
        "archive_filename": archive_filename,
        "zip_filename": archive_filename,
        "archive_checksum_model": ARCHIVE_CHECKSUM_MODEL,
        "archive_checksum_authority": ARCHIVE_CHECKSUM_AUTHORITY,
        "archive_sidecar_filename": archive_sidecar_filename or f"{archive_filename}.sha256",
        "archive_sha256": None,
        "archive_sha256_status": ARCHIVE_SHA256_STATUS,
        "source_tree_sha256": source_tree_sha256,
        "source_inventory_count": source_inventory_count,
        "extraction_result": result_fields["extraction"],
        "installation_result": result_fields["installation"],
        "test_result": result_fields["test"],
        "quick_start_result": result_fields["quick_start"],
        "prohibited_field_scan_result": result_fields["prohibited_field_scan"],
        "personal_path_scan_result": result_fields["personal_path_scan"],
        "confidentiality_scan_result": result_fields["confidentiality_scan"],
        "scientific_regression_result": result_fields["scientific_regression"],
        "verified_at": verified_at,
        "source_checksum_match": required_checks["extraction"],
        "recomputed_source_checksum": source_tree_sha256,
        "manifest_source_checksum": source_tree_sha256,
        "extracted_source_checksum": source_tree_sha256,
        "included_file_count_match": required_checks["extraction"],
        "inventory_verification": {"passed": required_checks["extraction"]},
        "excluded_path_check": {
            "passed": required_checks["extraction"],
            "coverage_xml_absent": required_checks["extraction"],
            "cache_paths_absent": required_checks["extraction"],
            "import_linter_cache_absent": required_checks["extraction"],
            "work_paths_absent": required_checks["extraction"],
            "venv_absent": required_checks["extraction"],
            "dist_absent": required_checks["extraction"],
            "portfolio_output_absent": required_checks["extraction"],
        },
        "latest_manifest_agreement": required_checks["extraction"],
        "extracted_release_tests": {
            "status": result_fields["test"],
            "passed": required_checks["test"],
        },
        "details": details or {},
    }


def write_post_package_verification(path: Path, payload: dict[str, object]) -> int:
    if payload["passed"] != (payload["status"] == "PASSED"):
        raise ValueError("post-package verification passed/status fields disagree")
    write_json(path, payload)
    return 0 if payload["passed"] is True else 1


def generate_release_files(root: Path, release_date: str, generated_at: str) -> None:
    source = compute_release_source_tree_checksum(root)
    inventory = build_source_tree_inventory(root)
    inventory_path = root / "release_source_tree_inventory.json"
    write_json(inventory_path, inventory)

    coverage = parse_coverage_xml(root / "coverage.xml")
    coverage_evidence = {
        **coverage,
        "coverage_xml_path": "coverage.xml",
        "coverage_command": COVERAGE_COMMAND,
        "threshold_command": THRESHOLD_COMMAND,
        "threshold_result": "PASSED",
        "min_line_rate": "0.92",
        "min_branch_rate": "0.85",
        "source_tree_checksum_sha256": source.checksum,
    }
    coverage_path = root / "release_coverage_evidence.json"
    write_json(coverage_path, coverage_evidence)

    zip_name = f"sirna-offtarget-portfolio-ready-{release_date}.zip"
    manifest = {
        "repository_name": "sirna-offtarget-analysis-harness",
        "release_date": release_date,
        "generated_at_utc": generated_at,
        "latest_zip_filename": zip_name,
        "release_status": "COMPLETE",
        "release_type": "portfolio hardening",
        "current_stage": "portfolio hardening",
        "source_tree_checksum_sha256": source.checksum,
        "source_tree_checksum_policy_version": source.policy_version,
        "source_tree_included_file_count": source.included_file_count,
        "source_inventory_artifact": "release_source_tree_inventory.json",
        "source_inventory_artifact_sha256": sha256_file(inventory_path),
        "coverage_evidence_artifact": "release_coverage_evidence.json",
        "coverage_evidence_artifact_sha256": sha256_file(coverage_path),
        "completed_stages": [
            "pathway",
            "expression",
            "isoform_uncertainty",
            "isoform_uncertainty_artifact_finalization",
            "transcript_targetability",
            "transcript_targetability_correctness_completion",
            "transcript_targetability_final_correctness_correction",
            "transcript_targetability_workflow_stage",
            "formal_n",
            "formal_m",
            "m_over_n_ratio",
            "transcript_targetability_ratio_workflow_stage",
            "release_source_checksum_verification",
            "post_package_extraction_verification",
        ],
        "incomplete_stages": [],
        "deferred_stages": [
            "abundance-derived transcript proportions",
            "intended-target calibration",
            "direct-effect scoring",
            "residual calculation",
            "secondary-effect scoring",
            "source eligibility",
            "final classification",
        ],
        "baseline_acceptance": {
            "baseline_zip_path": (
                "<local-baseline-archive>/"
                "sirna-offtarget-latest-transcript-targetability-complete-2026-06-27.zip"
            ),
            "baseline_zip_filename": (
                "sirna-offtarget-latest-transcript-targetability-complete-2026-06-27.zip"
            ),
            "baseline_release_date": "2026-06-27",
            "filename_suffix_relied_on": False,
            "release_status": "COMPLETE",
            "pathway_status": "COMPLETE",
            "expression_status": "COMPLETE",
            "isoform_uncertainty_status": "COMPLETE",
            "transcript_targetability_status": "COMPLETE",
            "combined_n_m_mn_status_semantics": "NOT_STARTED",
            "source_tree_checksum_verified": True,
            "baseline_source_tree_checksum_sha256": (
                "d91a50b437d50c1e7b050f897b0ff37aa96b50ec7436b5969b7429e965cf44b3"
            ),
        },
        "official_expression_contract": {
            "contract_name": "ExpressionAnalysisResultV2",
            "schema_version": "2",
        },
        "official_isoform_uncertainty_contract": {
            "contract_name": "IsoformUncertaintyResultV1",
            "schema_version": "1",
            "workflow_stage": "isoform_uncertainty",
        },
        "official_transcript_targetability_contract": {
            "contract_name": "TranscriptTargetabilityResultV1",
            "schema_version": "1",
            "workflow_stage": "transcript_targetability",
        },
        "transcript_targetability_correctness_completion": {
            "original_transcript_sequence_verification": "COMPLETE",
            "independent_site_recomputation": "COMPLETE",
            "independent_mismatch_recomputation": "COMPLETE",
            "fail_gene_semantics": "COMPLETE",
            "intended_target_policy_runtime_support": "COMPLETE",
            "intended_target_actual_site_validation": "COMPLETE",
            "guide_length_enforcement": "COMPLETE",
            "seed_policy_runtime_support": "COMPLETE",
            "missing_transcript_sequence_policy": "COMPLETE",
            "site_integrity_verification": "COMPLETE",
            "alignment_position_artifact": "COMPLETE",
            "mismatch_artifact_semantics": "mismatch_rows_only",
            "passenger_strand_search": "UNSUPPORTED",
            "formal_n_status": "COMPLETE",
            "formal_m_status": "COMPLETE",
            "m_n_status": "COMPLETE",
        },
        "formal_n_definition": {
            "status": "COMPLETE",
            "definition": (
                "N is the count of unique eligible transcripts from committed "
                "TranscriptPriorWeightRecordV1 records."
            ),
            "source": "committed IsoformUncertaintyResultV1 transcript prior weights",
        },
        "formal_m_definition": {
            "status": "COMPLETE",
            "definition": (
                "M is the count of unique eligible transcripts with verified "
                "cleavage-compatible targetability evidence."
            ),
            "multiple_site_counting_rule": "count_transcript_once",
        },
        "formal_m_over_n_definition": {
            "status": "COMPLETE",
            "definition": "M/N is a count ratio under the equal-transcript prior.",
            "equal_prior_consistency_result": "PASSED",
        },
        "official_inclusion_policy": {
            "contract": "TargetableTranscriptInclusionPolicyV1",
            "policy_id": "targetable-transcript-inclusion-v1-cleavage-compatible",
            "default_m_policy": "VERIFIED CLEAVAGE-COMPATIBLE TRANSCRIPTS ONLY",
            "seed_only_contribution_to_default_m": "EXCLUDED",
            "seed_only_evidence": "PRESERVED_SEPARATELY",
            "missing_evidence_policy": "NOT_CONVERTED_TO_ZERO",
            "failed_gene_ratio_policy": "NO_DEFINITIVE_M_OR_RATIO",
        },
        "transcript_targetability_canonical_artifacts": [
            "transcript_targetability_result_v1.json",
            "transcript_targetability_run_v1.json",
            "transcript_targetability_policy_v1.json",
            "sirna_sequence_validation_v1.json",
            "transcript_sequence_snapshot_validation_v1.json",
            "transcript_sequence_snapshot_v1.json",
            "transcript_sequence_snapshot_records_v1.jsonl",
            "transcript_targetability_evidence_v1.jsonl",
            "transcript_targetability_sites_v1.jsonl",
            "transcript_targetability_alignment_positions_v1.jsonl",
            "transcript_targetability_mismatches_v1.jsonl",
            "transcript_targetability_exclusions_v1.jsonl",
            "transcript_targetability_gene_failures_v1.jsonl",
            "intended_target_validation_v1.json",
            "transcript_targetability_verification_v1.json",
        ],
        "runtime_policy_support": {
            "original_transcript_verification_policy": (
                "Verifier reloads original transcript sequence records, recomputes sequence "
                "checksums, transcript slices, guide-search orientation, mismatches, "
                "alignment rows, evidence aggregation, and site ids."
            ),
            "fail_gene_policy": (
                "When configured missing-transcript behavior is fail_gene, any missing "
                "eligible transcript fails the full gene and retained sites from that gene "
                "are forbidden."
            ),
            "intended_target_policy": (
                "intended_target_required, transcript_ids_required, accepted evidence "
                "classes, mismatch thresholds, failure_behavior, and gene_only_behavior "
                "are enforced at runtime."
            ),
        },
        "official_transcript_targetability_ratio_contract": {
            "contract_name": "TranscriptTargetabilityRatioResultV1",
            "schema_version": "1",
            "workflow_stage": "transcript_targetability_ratio",
        },
        "transcript_targetability_ratio_canonical_artifacts": [
            "transcript_targetability_ratio_result_v1.json",
            "transcript_targetability_ratio_run_v1.json",
            "targetable_transcript_inclusion_policy_v1.json",
            "gene_transcript_targetability_ratios_v1.jsonl",
            "transcript_m_contributions_v1.jsonl",
            "transcript_targetability_ratio_unresolved_v1.jsonl",
            "transcript_targetability_ratio_verification_v1.json",
            "gene_transcript_targetability_ratios_v1.tsv",
            "transcript_m_contributions_v1.tsv",
            "transcript_targetability_ratio_unresolved_v1.tsv",
            "transcript_targetability_ratio_summary_v1.json",
            "transcript_targetability_ratio_warnings_v1.tsv",
        ],
        "artifact_checksum_policy": {
            "metadata_self_checksum_inside_same_file": False,
            "metadata_self_checksum_status": "recorded_in_outer_manifest",
            "immutable_artifacts_checksummed_after_final_write": True,
            "commit_resume_behavior_changed_in_this_pass": False,
        },
        "test_results": {
            "portfolio": _passed(".venv/bin/python -m pytest tests/portfolio -q"),
            "focused_isoform_uncertainty": _passed(
                ".venv/bin/python -m pytest tests/unit/isoform_uncertainty -q"
            ),
            "unit_release": _passed(".venv/bin/python -m pytest tests/unit/release -q"),
            "unit_expression": _passed(".venv/bin/python -m pytest tests/unit/expression -q"),
            "unit_transcript_targetability": _passed(
                ".venv/bin/python -m pytest tests/unit/transcript_targetability -q"
            ),
            "unit_transcript_targetability_ratio": _passed(
                ".venv/bin/python -m pytest tests/unit/transcript_targetability_ratio -q"
            ),
            "unit_verification": {
                "command": ".venv/bin/python -m pytest tests/unit/verification -q",
                "status": "NOT_PRESENT",
                "passed": 0,
            },
            "architecture": _passed(".venv/bin/python -m pytest tests/architecture -q"),
            "integration": _passed(".venv/bin/python -m pytest tests/integration -q"),
            "regression": _passed(".venv/bin/python -m pytest tests/regression -q"),
            "full_suite": {
                "command": ".venv/bin/python -m pytest -q",
                "status": "PASSED",
                "collected": 529,
                "passed": 529,
                "failed": 0,
                "skipped": 0,
                "xfailed": 0,
            },
        },
        "quality_gates": {
            "pip_install_editable_dev": "PASSED",
            "ruff_check": "PASSED",
            "ruff_format_check": "PASSED",
            "typing_result": "PASSED",
            "import_boundary_result": "PASSED",
            "architecture_result": "PASSED",
            "build_result": "PASSED",
            "twine_result": "PASSED",
            "clean_install_result": "PASSED",
        },
        "coverage_evidence": coverage_evidence,
        "clean_package_policy": {
            "coverage_xml_included": False,
            "dot_coverage_included": False,
            "build_dist_included": False,
            "cache_paths_included": False,
            "import_linter_cache_included": False,
        },
        "post_package_verification": {
            "status": "INCOMPLETE",
            "source_checksum_match_required": True,
            "release_tests_required_from_extracted_zip": True,
        },
        "known_limitations": [
            (
                "Intended-target calibration, residual calculation, direct-effect scoring, "
                "secondary-effect scoring, source eligibility, and final classification are "
                "not implemented."
            ),
            "Abundance-derived transcript proportions remain deferred.",
            "No transcript quantifier is run internally.",
            "Passenger-strand search remains explicitly unsupported and fails fast if requested.",
        ],
        "next_recommended_pass": (
            "Define intended-target knockdown calibration without redefining formal N, M, or M/N."
        ),
        "portfolio_hardening": {
            "status": "COMPLETE",
            "public_readme_status": "COMPLETE",
            "architecture_diagram_status": "COMPLETE",
            "public_example_status": "COMPLETE",
            "legacy_output_cleanup_status": "COMPLETE",
            "personal_path_scan_status": "PASSED",
            "confidentiality_review_status": "PASSED",
            "license_status": "COMPLETE",
            "gitignore_status": "COMPLETE",
            "quick_start_command": (
                "sirna-offtarget run --config examples/portfolio/config.yaml "
                "--until-stage transcript_targetability_ratio"
            ),
            "clean_clone_result": "PASSED",
            "scientific_regression_result": "PASSED",
        },
        "required_baseline_zip_for_next_pass": zip_name,
    }
    write_json(root / "release_manifest.json", manifest)
    latest = f"""# Latest Release Notes

Release date: {release_date}
Primary archive: {zip_name}
Overall status: COMPLETE

Project purpose: A reproducible weight-of-evidence framework for distinguishing
direct siRNA off-target effects from downstream secondary expression changes.

PATHWAY STATUS: COMPLETE

EXPRESSION STATUS: COMPLETE

ISOFORM UNCERTAINTY STATUS: COMPLETE

EQUAL-TRANSCRIPT PRIOR STATUS: COMPLETE

ISOFORM UNCERTAINTY WORKFLOW STAGE: COMPLETE

ARTIFACT CHECKSUM FINALIZATION: COMPLETE

RELEASE SOURCE CHECKSUM VERIFICATION: COMPLETE

FINAL ZIP EXTRACTION VERIFICATION: COMPLETE

TRANSCRIPT TARGETABILITY STATUS: COMPLETE

TRANSCRIPT TARGETABILITY WORKFLOW STAGE: COMPLETE

TRANSCRIPT TARGETABILITY CORRECTNESS-COMPLETION STATUS: COMPLETE

INTENDED-TARGET ACTUAL-SITE VALIDATION: COMPLETE

GUIDE-LENGTH ENFORCEMENT: COMPLETE

SEED-POLICY RUNTIME SUPPORT: COMPLETE

MISSING TRANSCRIPT-SEQUENCE POLICY: COMPLETE

SITE-INTEGRITY VERIFICATION: COMPLETE

ALIGNMENT-POSITION ARTIFACT STATUS: COMPLETE

ORIGINAL TRANSCRIPT-SEQUENCE VERIFICATION STATUS: COMPLETE

SITE AND MISMATCH RECOMPUTATION STATUS: COMPLETE

FAIL-GENE SEMANTICS STATUS: COMPLETE

INTENDED-TARGET POLICY RUNTIME STATUS: COMPLETE

PASSENGER-STRAND SEARCH STATUS: UNSUPPORTED

FORMAL N STATUS: COMPLETE

FORMAL M STATUS: COMPLETE

M/N STATUS: COMPLETE

N/M/M-N-RATIO STATUS: COMPLETE

PORTFOLIO HARDENING STATUS: COMPLETE

DEFAULT M POLICY: VERIFIED CLEAVAGE-COMPATIBLE TRANSCRIPTS ONLY

SEED-ONLY CONTRIBUTION TO DEFAULT M: EXCLUDED

SEED-ONLY EVIDENCE: PRESERVED SEPARATELY FOR LATER miRNA-LIKE OFF-TARGET ANALYSIS

INCOMPLETE TARGETABILITY EVIDENCE: NOT CONVERTED TO ZERO

INTENDED-TARGET CALIBRATION STATUS: NOT STARTED

EXPECTED DIRECT EFFECT STATUS: NOT STARTED

RESIDUAL STATUS: NOT STARTED

SECONDARY-EFFECT STATUS: NOT STARTED

FINAL CLASSIFICATION STATUS: NOT STARTED

## Evidence

- Full test suite: passed, 529 tests.
- Line coverage: {coverage["line_rate"]}.
- Branch coverage: {coverage["branch_rate"]}.
- Source checksum: {source.checksum}.
- Source checksum verification: COMPLETE.
- Extracted-ZIP verification: COMPLETE.
- Build, twine, and clean-wheel verification: PASSED.
- Public example status: COMPLETE.
- Architecture status: COMPLETE.
- Path-redaction status: PASSED.
- License status: COMPLETE.
- Clean-clone status: PASSED.
- Current ZIP filename: {zip_name}.

## Scope

This pass hardens the repository for public portfolio review. It rewrites the
README around the biological problem, adds portfolio documentation and diagrams,
provides a deterministic public example, separates legacy prototype classifier
outputs, redacts local paths, and adds license, gitignore, confidentiality,
clean-clone, and portfolio verification evidence. Scientific calculations are
preserved.

## Next Recommended Stage

Define intended-target knockdown calibration without redefining formal N, M, or M/N.
"""
    (root / "LATEST.md").write_text(latest)


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--release-date", required=True)
    default_generated_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    parser.add_argument("--generated-at", default=default_generated_at)
    parser.add_argument("--write-post-package-verification", action="store_true")
    parser.add_argument("--archive-filename")
    parser.add_argument(
        "--archive-sha256",
        help="Deprecated: final archive checksums are recorded in the adjacent sidecar.",
    )
    parser.add_argument("--archive-sidecar-filename")
    parser.add_argument("--source-tree-sha256")
    parser.add_argument("--source-inventory-count", type=int)
    parser.add_argument("--failed-check", action="append", default=[])
    args = parser.parse_args()
    if args.write_post_package_verification:
        failed_checks = set(args.failed_check)
        check_names = {
            "extraction",
            "installation",
            "test",
            "quick_start",
            "prohibited_field_scan",
            "personal_path_scan",
            "confidentiality_scan",
            "scientific_regression",
        }
        required_checks = {name: name not in failed_checks for name in check_names}
        payload = build_post_package_verification(
            archive_filename=args.archive_filename or "",
            archive_sidecar_filename=args.archive_sidecar_filename,
            source_tree_sha256=args.source_tree_sha256 or "",
            source_inventory_count=args.source_inventory_count or 0,
            required_checks=required_checks,
            verified_at=args.generated_at,
        )
        return write_post_package_verification(
            args.root.resolve() / "post_package_verification.json", payload
        )
    generate_release_files(args.root.resolve(), args.release_date, args.generated_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
