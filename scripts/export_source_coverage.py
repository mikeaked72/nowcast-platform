from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowcast.source_coverage import export_source_coverage


def main() -> int:
    parser = argparse.ArgumentParser(description="Export data-store source coverage for the static site.")
    parser.add_argument("--manifest-path", default="store/manifest.json", help="Data-store manifest path")
    parser.add_argument("--publish-dir", default="site/data", help="Site data root")
    parser.add_argument("--countries-path", help="Optional countries.json path")
    args = parser.parse_args()

    try:
        out_path = export_source_coverage(
            manifest_path=Path(args.manifest_path),
            publish_dir=Path(args.publish_dir),
            countries_path=Path(args.countries_path) if args.countries_path else None,
        )
    except Exception as exc:
        print(f"export_source_coverage failed: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
