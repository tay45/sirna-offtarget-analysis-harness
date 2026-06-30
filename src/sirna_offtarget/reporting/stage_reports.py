from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.checkpoints import current_manifest_path
from sirna_offtarget.execution.dag import STAGE_ORDER, stage_index
from sirna_offtarget.execution.hashing import load_json


def collect_stage_report_links(run_dir: Path) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for stage in STAGE_ORDER:
        sdir = run_dir / "stages" / f"{stage_index(stage):02d}_{stage}"
        manifest_path = current_manifest_path(sdir)
        if manifest_path is None:
            continue
        manifest = load_json(manifest_path)
        reports = manifest.get("report_paths", {})
        json_report = Path(str(reports.get("json", "")))
        html_report = Path(str(reports.get("html", "")))
        links.append(
            {
                "stage": stage,
                "status": str(manifest.get("status")),
                "json": str(json_report.relative_to(run_dir))
                if json_report.is_absolute() and json_report.is_relative_to(run_dir)
                else str(json_report),
                "html": str(html_report.relative_to(run_dir))
                if html_report.is_absolute() and html_report.is_relative_to(run_dir)
                else str(html_report),
            }
        )
    return links
