from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirna_offtarget.pathway.providers.base import load_cached_records


def test_load_cached_records_supports_json_jsonl_csv_and_empty(tmp_path: Path) -> None:
    (tmp_path / "jsonprov.json").write_text(json.dumps({"records": [{"a": "1", "b": None}]}))
    snapshot = load_cached_records(tmp_path, "jsonprov", ("a", "b"))
    assert snapshot.as_dict()["record_count"] == 1
    assert snapshot.records[0]["b"] == ""

    (tmp_path / "lines.jsonl").write_text('{"a":"1"}\n')
    assert load_cached_records(tmp_path, "lines", ("a",)).record_count == 1

    (tmp_path / "csvprov.csv").write_text("a,b\n1,2\n")
    assert load_cached_records(tmp_path, "csvprov", ("a", "b")).record_count == 1

    (tmp_path / "empty.tsv").write_text("a\tb\n")
    assert load_cached_records(tmp_path, "empty", ("a", "b")).record_count == 0


def test_load_cached_records_rejects_missing_and_malformed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_cached_records(tmp_path, "missing", ("a",))
    (tmp_path / "bad.json").write_text(json.dumps({"records": {"not": "a list"}}))
    with pytest.raises(ValueError):
        load_cached_records(tmp_path, "bad", ("a",))
    (tmp_path / "badrecord.json").write_text(json.dumps([1]))
    with pytest.raises(ValueError):
        load_cached_records(tmp_path, "badrecord", ("a",))
    (tmp_path / "missingcol.tsv").write_text("a\n1\n")
    with pytest.raises(ValueError):
        load_cached_records(tmp_path, "missingcol", ("a", "b"))
