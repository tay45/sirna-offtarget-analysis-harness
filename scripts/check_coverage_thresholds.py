from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("coverage_xml", type=Path)
    parser.add_argument("--min-line-rate", type=float, default=0.92)
    parser.add_argument("--min-branch-rate", type=float, default=0.85)
    args = parser.parse_args()

    root = ET.parse(args.coverage_xml).getroot()
    line_rate = float(root.attrib.get("line-rate", "0"))
    branch_rate = float(root.attrib.get("branch-rate", "0"))
    failures = []
    if line_rate < args.min_line_rate:
        failures.append(f"line-rate {line_rate:.4f} < {args.min_line_rate:.4f}")
    if branch_rate < args.min_branch_rate:
        failures.append(f"branch-rate {branch_rate:.4f} < {args.min_branch_rate:.4f}")
    if failures:
        print("; ".join(failures))
        return 1
    print(f"coverage thresholds passed: line-rate={line_rate:.4f}, branch-rate={branch_rate:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
