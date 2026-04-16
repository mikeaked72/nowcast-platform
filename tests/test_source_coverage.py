from __future__ import annotations

import json
from pathlib import Path

from nowcast.source_coverage import export_source_coverage


def test_export_source_coverage_summarises_manifest(tmp_path: Path) -> None:
    manifest = {
        "last_full_update": "2026-04-16T05:49:26Z",
        "series": {
            "BRA_POLICY_RATE": {"rows": 49, "source": "imf:MFS_IR:KEY", "status": "OK"},
            "BRA_EXCHANGE_RATE": {"rows": 75, "source": "imf:ER:KEY", "status": "OK"},
            "DEU_INDPRO_M": {"rows": 314, "source": "eurostat:sts_inpr_m", "status": "OK"},
            "DEU_OLD_KEY": {"rows": 0, "source": "eurostat:discovery", "status": "SKIPPED"},
        },
        "processed": {
            "monthly": {
                "rows": 120,
                "columns": 3,
                "start": "2020-01-31",
                "end": "2026-03-31",
                "path": "store/processed/monthly.parquet",
            }
        },
    }
    publish_dir = tmp_path / "site" / "data"
    publish_dir.mkdir(parents=True)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (publish_dir / "countries.json").write_text(
        json.dumps([
            {"code": "br", "name": "Brazil", "enabled": True, "default_target": "GDP", "indicators": []},
            {"code": "de", "name": "Germany", "enabled": True, "default_target": "GDP", "indicators": []},
        ]),
        encoding="utf-8",
    )

    out_path = export_source_coverage(manifest_path=tmp_path / "manifest.json", publish_dir=publish_dir)

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["series_count"] == 4
    assert payload["status_counts"] == {"OK": 3, "SKIPPED": 1}
    assert payload["processed"][0]["frequency"] == "monthly"
    countries = {country["code"]: country for country in payload["countries"]}
    assert countries["br"]["ok_count"] == 2
    assert countries["de"]["skipped_count"] == 1
