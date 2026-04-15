from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowcast.pipeline import run_countries_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run publish scaffold for multiple countries.")
    parser.add_argument("--countries", required=True, help="Comma-separated country codes")
    parser.add_argument("--publish-dir", default="site/data", help="Publish data root")
    parser.add_argument("--packs-dir", default="country_packs", help="Country packs directory")
    parser.add_argument("--input-dir", default="runs/input", help="Downloaded model input root")
    parser.add_argument("--source-dir", default="runs/source", help="Downloaded source data root")
    parser.add_argument("--skip-model-run", action="store_true", help="Publish from existing input only")
    parser.add_argument("--no-download", action="store_true", help="Use existing source files without downloading")
    args = parser.parse_args()

    countries = [country.strip() for country in args.countries.split(",") if country.strip()]
    if not countries:
        print("run_all_countries failed: no countries supplied", file=sys.stderr)
        return 1

    try:
        run_countries_pipeline(
            countries,
            publish_dir=Path(args.publish_dir),
            packs_dir=Path(args.packs_dir),
            input_dir=Path(args.input_dir),
            source_dir=Path(args.source_dir),
            skip_model_run=args.skip_model_run,
            download=not args.no_download,
            validate=False,
        )
    except Exception as exc:
        print(f"run_all_countries failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
