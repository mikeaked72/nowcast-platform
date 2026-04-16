from __future__ import annotations

from datetime import date

from nowcast.g10.fred_md import load_vintage_csv


def test_load_fred_md_style_vintage_csv(tmp_path) -> None:
    fixture = tmp_path / "2026-03.csv"
    fixture.write_text(
        "sasdate,INDPRO,PAYEMS\n"
        "Transform:,5,5\n"
        "2026-01-01,100,200\n"
        "2026-02-01,101,202\n",
        encoding="utf-8",
    )

    frame = load_vintage_csv(fixture, vintage_date=date(2026, 3, 1), freq="M")

    assert set(frame.columns) >= {"date", "series_id", "value", "freq", "tcode", "vintage_date", "vintage_kind"}
    assert len(frame) == 4
    assert set(frame["series_id"]) == {"INDPRO", "PAYEMS"}
    assert set(frame["tcode"]) == {5}
    assert set(frame["vintage_kind"]) == {"real"}


def test_load_fixture_without_tcode_row_defaults_to_levels(tmp_path) -> None:
    fixture = tmp_path / "current.csv"
    fixture.write_text(
        "sasdate,INDPRO\n"
        "2026-01-01,100\n",
        encoding="utf-8",
    )

    frame = load_vintage_csv(fixture, vintage_date=date(2026, 2, 1), freq="M")

    assert frame.iloc[0]["series_id"] == "INDPRO"
    assert frame.iloc[0]["tcode"] == 1

