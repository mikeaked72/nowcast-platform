import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = ROOT / "specs" / "candidate_mappings.csv"

REQUIRED_COLUMNS = {
    "country",
    "concept",
    "source",
    "flow",
    "series_key",
    "frequency",
    "units",
    "test_status",
    "notes",
}

VALID_STATUSES = {"UNTESTED", "OK", "EMPTY", "ERROR", "NEEDS_KEY", "NEEDS_REVIEW"}


def test_candidate_mapping_contract():
    assert MAPPINGS.exists()
    with MAPPINGS.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert REQUIRED_COLUMNS.issubset(reader.fieldnames or [])
        rows = list(reader)

    assert rows
    for row in rows:
        for column in REQUIRED_COLUMNS - {"notes"}:
            assert row[column]
        assert row["test_status"] in VALID_STATUSES


def test_candidate_mapping_has_priority_sources():
    rows = list(csv.DictReader(MAPPINGS.open(newline="", encoding="utf-8")))
    sources = {row["source"] for row in rows}
    assert {"imf", "bundesbank", "boj_flatfile", "ecb", "eurostat"}.issubset(sources)
