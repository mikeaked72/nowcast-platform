"""Command line interface for the nowcast package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nowcast.pipeline import parse_as_of, run_country_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nowcast.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one country nowcast and publish outputs")
    run_parser.add_argument("--country", required=True, help="Country code, for example us")
    run_parser.add_argument("--publish-dir", default="site/data", help="Publish data root or country directory")
    run_parser.add_argument("--packs-dir", default="country_packs", help="Country packs directory")
    run_parser.add_argument("--input-dir", default="runs/input", help="Model input root")
    run_parser.add_argument("--input-path", help="Explicit model input CSV path")
    run_parser.add_argument("--source-dir", default="runs/source", help="Downloaded source data root")
    run_parser.add_argument("--as-of", help="YYYY-MM-DD or YYYY-MM cutoff for publishing history")
    run_parser.add_argument("--skip-model-run", action="store_true", help="Publish from existing input only")
    run_parser.add_argument("--no-download", action="store_true", help="Use existing source files without downloading")
    run_parser.add_argument("--no-validate", action="store_true", help="Skip output contract validation")

    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            result = run_country_pipeline(
                args.country,
                publish_dir=Path(args.publish_dir),
                packs_dir=Path(args.packs_dir),
                input_dir=Path(args.input_dir),
                input_path=Path(args.input_path) if args.input_path else None,
                source_dir=Path(args.source_dir),
                as_of=parse_as_of(args.as_of),
                skip_model_run=args.skip_model_run,
                download=not args.no_download,
                validate=not args.no_validate,
            )
        except Exception as exc:
            print(f"nowcast run failed: {exc}", file=sys.stderr)
            return 1

        print(f"published {result.country_code} to {result.country_publish_dir}")
        print(f"model input {result.input_path}")
        return 0

    parser.error(f"unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
