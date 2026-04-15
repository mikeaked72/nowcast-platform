"""Quick diagnostic: print all series IDs in RBA tables d2 and d3."""
import csv
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "store" / "raw" / "rba"

for table in ["d2", "d3"]:
    path = RAW / f"{table}.csv"
    if not path.exists():
        print(f"{table}: file not found at {path}")
        continue
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    max_len = max(len(r) for r in rows[:25])
    rows = [r + [""] * (max_len - len(r)) for r in rows[:25]]
    id_row = rows[10]
    title_row = rows[1]
    print(f"\n=== {table.upper()} — all series ===")
    for sid, title in zip(id_row, title_row):
        s = sid.strip()
        skip = (not s) or (s == "Series ID")
        if not skip:
            print(f"  {s:<22} {title[:65]}")
