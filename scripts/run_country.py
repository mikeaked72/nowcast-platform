from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowcast.pipeline import parse_as_of, run_country_pipeline
from nowcast.publish import validate_country_pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one country publish scaffold.")
    parser.add_argument("--country", required=True, help="Country code, for example us")
    parser.add_argument("--publish-dir", default="site/data", help="Publish data root or country directory")
    parser.add_argument("--packs-dir", default="country_packs", help="Country packs directory")
    parser.add_argument("--input-dir", default="runs/input", help="Downloaded model input root")
    parser.add_argument("--input-path", help="Explicit model input CSV path")
    parser.add_argument("--source-dir", default="runs/source", help="Downloaded source data root")
    parser.add_argument("--skip-model-run", action="store_true", help="Publish from existing input only")
    parser.add_argument("--no-download", action="store_true", help="Use existing source files without downloading")
    parser.add_argument("--as-of", help="As-of date in YYYY-MM-DD form")
    parser.add_argument("--validate-pack-only", action="store_true", help="Only validate the country pack")
    args = parser.parse_args()

    try:
        validate_country_pack(args.country, args.packs_dir)
        if args.validate_pack_only:
            return 0

        run_country_pipeline(
            args.country,
            publish_dir=Path(args.publish_dir),
            packs_dir=Path(args.packs_dir),
            input_dir=Path(args.input_dir),
            input_path=Path(args.input_path) if args.input_path else None,
            source_dir=Path(args.source_dir),
            as_of=parse_as_of(args.as_of),
            skip_model_run=args.skip_model_run,
            download=not args.no_download,
            validate=False,
        )
    except Exception as exc:
        print(f"run_country failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
