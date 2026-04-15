"""
Discover and test candidate macro data mappings.

This script does not download production raw data. It probes provider metadata
and a curated candidate table, then writes machine-readable discovery outputs:

    specs/candidate_mappings.csv
    specs/source_discovery_summary.json

The table is intentionally provisional. A candidate that downloads still needs
human/model review for concept fit, frequency, units, timeliness, and revision
behaviour before it is promoted into an ingestor catalog.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import pandas as pd
import requests

try:
    from ingest.common import add_common_args, configure_logging, retry_call
except ImportError:
    from pipeline.ingest.common import add_common_args, configure_logging, retry_call


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPECS = ROOT / "specs"
DEFAULT_CANDIDATES = SPECS / "candidate_mappings.csv"
DEFAULT_SUMMARY = SPECS / "source_discovery_summary.json"

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

FIELDNAMES = [
    "country",
    "concept",
    "source",
    "flow",
    "series_key",
    "frequency",
    "units",
    "priority",
    "test_status",
    "rows",
    "start",
    "end",
    "last_tested",
    "notes",
]


@dataclass
class Candidate:
    country: str
    concept: str
    source: str
    flow: str
    series_key: str
    frequency: str
    units: str
    priority: str = "candidate"
    test_status: str = "UNTESTED"
    rows: str = ""
    start: str = ""
    end: str = ""
    last_tested: str = ""
    notes: str = ""


SEED_CANDIDATES = [
    Candidate("BRA", "cpi", "imf", "CPI", "BRA.CPI._T.IX.M", "monthly", "index", "fallback", notes="Current IMF SDMX 2.1 CPI pattern; good cross-country fallback."),
    Candidate("BRA", "inflation", "imf", "CPI", "BRA.CPI._T.YOY_PCH_PA_PT.M", "monthly", "percent_yoy", "fallback", notes="Current IMF SDMX 2.1 CPI percent-change pattern."),
    Candidate("BRA", "policy_rate", "imf", "MFS_IR", "BRA.FPOLM_PA.M", "monthly", "percent_pa", "discovery", notes="Dimension map still provisional; expected to need codelist lookup."),
    Candidate("BRA", "exchange_rate", "imf", "MFS_FMP", "BRA.ENDA_XDC_USD_RATE.M", "monthly", "local_per_usd", "discovery", notes="Dimension map still provisional; expected to need codelist lookup."),
    Candidate("BRA", "unemployment", "imf", "IFS", "BRA.LUR_PT.M", "monthly", "percent", "discovery", notes="Dimension map still provisional; may move to a labour-specific IMF dataflow."),
    Candidate("DEU", "government_yield_2y", "bundesbank", "BBSIS", "M.I.ZST.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A", "monthly", "percent_pa", "preferred", notes="Verified BBSIS term-structure key."),
    Candidate("DEU", "government_yield_5y", "bundesbank", "BBSIS", "M.I.ZST.ZI.EUR.S1311.B.A604.R05XX.R.A.A._Z._Z.A", "monthly", "percent_pa", "preferred", notes="Verified BBSIS term-structure key."),
    Candidate("DEU", "government_yield_10y", "bundesbank", "BBSIS", "M.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A", "monthly", "percent_pa", "preferred", notes="Verified BBSIS term-structure key."),
    Candidate("DEU", "household_credit", "bundesbank", "BBKRT", "BBKRT.M.U.NS.A.A.A.AB.A.A.PUR.A.A", "monthly", "unknown", "discovery", notes="Legacy key fails; use discovery output to find current credit key."),
    Candidate("DEU", "nfc_credit", "bundesbank", "BBKRT", "BBKRT.M.U.NS.A.A.A.NF.A.A.PUR.A.A", "monthly", "unknown", "discovery", notes="Legacy key fails; use discovery output to find current credit key."),
    Candidate("JPN", "producer_prices", "boj_flatfile", "flatfile", "https://www.stat-search.boj.or.jp/info/cgpi_m_en.zip", "monthly", "index", "preferred", notes="Current public CGPI flat-file package."),
    Candidate("JPN", "current_account", "boj_flatfile", "flatfile", "https://www.stat-search.boj.or.jp/info/bp_m_en.zip", "monthly", "jpy", "candidate", notes="Current public BoP flat-file package; inspect columns before promotion."),
    Candidate("JPN", "policy_rate", "boj_api", "search", "MADR1Z@D", "daily", "percent_pa", "discovery", notes="Legacy API code currently fails; replace with current API or flat-file package."),
    Candidate("JPN", "money_base", "boj_api", "search", "MD01'MABASE1@M", "monthly", "jpy", "discovery", notes="Legacy API code currently fails; replace with current API or flat-file package."),
    Candidate("GBR", "government_yield_5y", "boe", "IADB", "IUDSNZC", "daily", "percent_pa", "preferred", notes="Verified Bank of England IADB zero-coupon yield key."),
    Candidate("GBR", "government_yield_10y", "boe", "IADB", "IUDMNZC", "daily", "percent_pa", "preferred", notes="Verified Bank of England IADB zero-coupon yield key."),
    Candidate("GBR", "government_yield_20y", "boe", "IADB", "IUDLNZC", "daily", "percent_pa", "candidate", notes="Verified Bank of England IADB zero-coupon yield key; fills long-tenor curve until a current 30y key is identified."),
    Candidate("GBR", "government_yield_2y", "boe", "IADB", "TBD", "daily", "percent_pa", "discovery", "NEEDS_KEY", notes="Current IADB 2y code still needs discovery."),
    Candidate("GBR", "government_yield_30y", "boe", "IADB", "TBD", "daily", "percent_pa", "discovery", "NEEDS_KEY", notes="Current IADB 30y code still needs discovery."),
    Candidate("EA", "policy_rate", "ecb", "FM", "D.U2.EUR.4F.KR.DFR.LEV", "daily", "percent_pa", "preferred", notes="ECB deposit facility rate."),
    Candidate("EA", "exchange_rate", "ecb", "EXR", "D.USD.EUR.SP00.A", "daily", "usd_per_eur", "preferred", notes="ECB EUR/USD reference rate."),
    Candidate("EA", "inflation", "ecb", "ICP", "M.U2.N.000000.4.ANR", "monthly", "percent_yoy", "preferred", notes="Euro area HICP all-items annual rate."),
    Candidate("EA", "real_gdp", "eurostat", "namq_10_gdp", "Q.CLV15_MEUR.SCA.B1GQ.EA20", "quarterly", "million_eur_chained", "preferred", notes="Euro area real GDP, chained volumes."),
    Candidate("EA", "unemployment", "eurostat", "une_rt_m", "M.SA.TOTAL.PC_ACT.T.EA20", "monthly", "percent", "preferred", notes="Eurostat monthly unemployment rate."),
    Candidate("DEU", "industrial_production", "eurostat", "sts_inpr_m", "TBD", "monthly", "index", "discovery", notes="Flow candidate only; discover current dimensions before testing."),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_candidates(path: Path) -> list[Candidate]:
    if not path.exists():
        return [Candidate(**asdict(c)) for c in SEED_CANDIDATES]
    rows: list[Candidate] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(Candidate(**{k: row.get(k, "") for k in FIELDNAMES}))
    existing = {(r.country, r.concept, r.source, r.flow, r.series_key) for r in rows}
    for candidate in SEED_CANDIDATES:
        key = (candidate.country, candidate.concept, candidate.source, candidate.flow, candidate.series_key)
        if key not in existing:
            rows.append(Candidate(**asdict(candidate)))
    return rows


def write_candidates(path: Path, candidates: Iterable[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(asdict(candidate))


def parse_sdmx_dataflows(text: str, keywords: Iterable[str]) -> dict:
    ns = {
        "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
        "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
    }
    root = ET.fromstring(text)
    flows = []
    words = tuple(k.lower() for k in keywords)
    for node in root.findall(".//str:Dataflow", ns):
        flow_id = node.attrib.get("id", "")
        name_node = node.find("com:Name", ns)
        name = "" if name_node is None else (name_node.text or "")
        if not words or any(w in f"{flow_id} {name}".lower() for w in words):
            flows.append({
                "id": flow_id,
                "agency": node.attrib.get("agencyID", ""),
                "name": name,
            })
    return {"count": len(root.findall(".//str:Dataflow", ns)), "matches": flows[:50]}


def get_text(url: str, *, params: dict | None = None, timeout: int = 60) -> requests.Response:
    response = retry_call(
        lambda: requests.get(url, params=params, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=timeout),
        label=url,
    )
    response.raise_for_status()
    return response


def discover_metadata() -> dict:
    summary: dict[str, object] = {"generated_at": now_iso(), "providers": {}}
    providers = summary["providers"]

    probes = {
        "imf": ("https://api.imf.org/external/sdmx/2.1/dataflow/all/all/latest", ("CPI", "IFS", "MFS", "BOP", "labour", "financial")),
        "ecb": ("https://data-api.ecb.europa.eu/service/dataflow/all/all/latest", ("FM", "EXR", "ICP", "BSI", "MIR", "MNA", "LFSI", "STS")),
        "eurostat": ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/all/latest", ("gdp", "hicp", "unemployment", "prices", "production", "trade")),
    }
    for name, (url, keywords) in probes.items():
        try:
            response = get_text(url, timeout=120)
            providers[name] = {"status": "OK", **parse_sdmx_dataflows(response.text, keywords)}
        except Exception as exc:
            providers[name] = {"status": "ERROR", "error": str(exc)}

    try:
        response = get_text("https://www.stat-search.boj.or.jp/info/dload_en.html", timeout=60)
        links = sorted(set(re.findall(r'href="([^"]+\.(?:zip|csv))"', response.text, flags=re.I)))
        full_links = [
            link if link.startswith("http") else f"https://www.stat-search.boj.or.jp/info/{link.lstrip('./')}"
            for link in links
        ]
        providers["boj"] = {"status": "OK", "download_links": full_links[:100], "count": len(full_links)}
    except Exception as exc:
        providers["boj"] = {"status": "ERROR", "error": str(exc)}

    try:
        response = get_text("https://api.statistiken.bundesbank.de/rest/data/BBSIS/M.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A", params={"format": "csv", "lang": "en", "startPeriod": "2025-01"}, timeout=60)
        providers["bundesbank"] = {"status": "OK", "probe": "BBSIS term-structure data endpoint", "bytes": len(response.text)}
    except Exception as exc:
        providers["bundesbank"] = {"status": "ERROR", "error": str(exc)}

    return summary


def candidate_url(candidate: Candidate) -> tuple[str, dict, dict]:
    source = candidate.source.lower()
    headers = {"User-Agent": UA, "Accept": "text/csv, application/vnd.sdmx.data+csv, */*"}
    if source == "imf":
        return (
            f"https://api.imf.org/external/sdmx/2.1/data/{candidate.flow}/{candidate.series_key}",
            {"startPeriod": "2025"},
            headers,
        )
    if source == "bundesbank":
        start = "2025-01" if candidate.series_key.startswith("M.") else "2025"
        return (
            f"https://api.statistiken.bundesbank.de/rest/data/{candidate.flow}/{candidate.series_key}",
            {"format": "csv", "lang": "en", "startPeriod": start},
            headers,
        )
    if source == "ecb":
        ecb_headers = dict(headers)
        ecb_headers["Accept"] = "text/csv"
        return (
            f"https://data-api.ecb.europa.eu/service/data/{candidate.flow}/{candidate.series_key}",
            {"startPeriod": "2025"},
            ecb_headers,
        )
    if source == "eurostat":
        return (
            f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{candidate.flow}/{candidate.series_key}".rstrip("/"),
            {"format": "SDMX-CSV", "detail": "dataonly", "startPeriod": "2025"},
            headers,
        )
    if source == "boj_api":
        return (
            "https://www.stat-search.boj.or.jp/api/v1/search",
            {"code": candidate.series_key, "format": "csv", "from": "202501"},
            headers,
        )
    if source == "boj_flatfile":
        return (candidate.series_key, {}, headers)
    if source == "boe":
        return (
            "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp",
            {
                "csv.x": "yes",
                "Datefrom": "01/Jan/2025",
                "Dateto": "",
                "SeriesCodes": candidate.series_key,
                "UsingCodes": "Y",
                "VPD": "Y",
                "VFD": "N",
            },
            headers,
        )
    raise ValueError(f"Unsupported source {candidate.source}")


def summarise_csv(text: str) -> tuple[int, str, str]:
    if text.lstrip().startswith("<"):
        raise ValueError("provider returned XML/HTML instead of CSV")

    date_pattern = re.compile(r'^"?(\d{4}(?:[-/]?(?:M)?\d{2})?(?:-Q[1-4])?)')
    line_dates: list[str] = []
    for line in text.splitlines():
        match = date_pattern.match(line.strip())
        if match:
            line_dates.append(match.group(1))

    try:
        df = pd.read_csv(StringIO(text), sep=None, engine="python", on_bad_lines="skip")
    except Exception:
        df = pd.read_csv(StringIO(text), low_memory=False)

    if df.empty:
        return 0, "", ""
    date_col = next((c for c in ("TIME_PERIOD", "date", "DATE", "TIME", "Date") if c in df.columns), None)
    if date_col is None:
        if line_dates:
            values = sorted(line_dates)
            return len(line_dates), values[0], values[-1]
        return int(df.shape[0]), "", ""
    values = df[date_col].dropna().astype(str).sort_values()
    if values.empty:
        if line_dates:
            values = sorted(line_dates)
            return len(line_dates), values[0], values[-1]
        return int(df.shape[0]), "", ""
    parsed = pd.to_datetime(values, errors="coerce", dayfirst=True)
    if parsed.notna().any():
        parsed = parsed.dropna().sort_values()
        return int(df.shape[0]), parsed.iloc[0].date().isoformat(), parsed.iloc[-1].date().isoformat()
    return int(df.shape[0]), values.iloc[0], values.iloc[-1]


def test_candidate(candidate: Candidate) -> Candidate:
    tested = Candidate(**asdict(candidate))
    tested.last_tested = now_iso()
    tested.notes = clear_probe_notes(tested.notes)

    if tested.source in {"boe", "eurostat"} and tested.series_key in {"", "TBD"}:
        tested.test_status = "NEEDS_KEY"
        tested.notes = append_note(tested.notes, "Flow discovered but no dimension key has been selected yet.")
        return tested

    try:
        url, params, headers = candidate_url(tested)
        response = retry_call(
            lambda: requests.get(url, params=params, headers=headers, timeout=120),
            label=f"{tested.source} {tested.flow}/{tested.series_key}",
        )
        response.raise_for_status()
        if tested.source == "boj_flatfile" and url.lower().endswith(".zip"):
            with zipfile.ZipFile(BytesIO(response.content)) as zf:
                csv_name = next(name for name in zf.namelist() if name.lower().endswith(".csv"))
                text = zf.read(csv_name).decode("utf-8-sig", errors="replace")
        else:
            text = response.text
        rows, start, end = summarise_csv(text)
        tested.rows = str(rows)
        tested.start = start
        tested.end = end
        if rows <= 0:
            tested.test_status = "EMPTY"
        elif tested.source in {"imf", "ecb", "eurostat", "bundesbank", "boj_api"} and not start:
            tested.test_status = "NEEDS_REVIEW"
            tested.notes = append_note(tested.notes, "Probe returned rows but no recognizable time-period column.")
        else:
            tested.test_status = "OK"
    except Exception as exc:
        tested.test_status = "ERROR"
        tested.notes = append_note(tested.notes, f"Probe failed: {exc}")
    return tested


def append_note(existing: str, extra: str) -> str:
    if not existing:
        return extra
    if extra in existing:
        return existing
    return f"{existing} {extra}"


def clear_probe_notes(notes: str) -> str:
    for marker in (" Probe failed:", "\nProbe failed:", " Flow discovered but no dimension key"):
        if marker in notes:
            notes = notes.split(marker, 1)[0]
    return notes.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover/test macro data source candidates")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--sources", default="", help="Comma-separated source filter, e.g. imf,bundesbank")
    parser.add_argument("--metadata-only", action="store_true", help="Only refresh source_discovery_summary.json")
    parser.add_argument("--no-network", action="store_true", help="Write seed table without live provider probes")
    add_common_args(parser)
    args = parser.parse_args()
    logger = configure_logging(args.verbose)

    source_filter = {s.strip().lower() for s in args.sources.split(",") if s.strip()}

    candidates = read_candidates(args.candidates)
    if not args.metadata_only and not args.no_network:
        logger.info("Testing %s candidate mappings", len(candidates))
        tested = []
        for candidate in candidates:
            if source_filter and candidate.source.lower() not in source_filter:
                tested.append(candidate)
                continue
            tested.append(test_candidate(candidate))
        candidates = tested
    write_candidates(args.candidates, candidates)

    if not args.no_network:
        logger.info("Refreshing provider metadata summary")
        summary = discover_metadata()
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    ok_count = sum(1 for c in candidates if c.test_status == "OK")
    print(f"Wrote {args.candidates} ({ok_count}/{len(candidates)} OK candidates)")
    if not args.no_network:
        print(f"Wrote {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
