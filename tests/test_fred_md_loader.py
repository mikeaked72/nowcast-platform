from __future__ import annotations

from datetime import date

from nowcast.g10.fred_md import (
    _first_csv_href,
    fred_fallback_current_vintage,
    fred_vintage_filename,
    fred_vintage_url,
    load_vintage_csv,
)


def test_fred_md_urls_use_current_st_louis_fed_media_paths() -> None:
    assert fred_vintage_url("fred_md").endswith("/monthly/current-md.csv")
    assert fred_vintage_url("fred_qd").endswith("/quarterly/current-qd.csv")
    assert fred_vintage_url("fred_md", "2026-03").endswith("/monthly/2026-03-md.csv")
    assert fred_vintage_url("fred_qd", "2026-03").endswith("/quarterly/2026-03-qd.csv")
    assert fred_vintage_filename("fred_md") == "current-md.csv"
    assert fred_vintage_filename("fred_qd", "2026-03") == "2026-03-qd.csv"


def test_discover_current_link_parser_accepts_dated_media_links() -> None:
    html = (
        '<a href="https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/'
        'fred-md/monthly/2026-03-md.csv">current.csv</a>'
        '<a href="https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/'
        'fred-md/quarterly/2026-03-qd.csv">current.csv</a>'
    )

    assert _first_csv_href(html, "monthly", "md").endswith("/2026-03-md.csv")
    assert _first_csv_href(html, "quarterly", "qd").endswith("/2026-03-qd.csv")


def test_fallback_current_vintage_uses_prior_calendar_month() -> None:
    assert fred_fallback_current_vintage(date(2026, 4, 17)) == "2026-03"
    assert fred_fallback_current_vintage(date(2026, 1, 5)) == "2025-12"


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
