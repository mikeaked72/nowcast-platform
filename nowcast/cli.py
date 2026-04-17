"""Command line interface for the nowcast package."""

from __future__ import annotations

import argparse
import json
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

    g10_check_parser = subparsers.add_parser("g10-check-config", help="Validate one G10 country config")
    g10_check_parser.add_argument("--iso", default="US", help="ISO country code, for example US")

    g10_assemble_parser = subparsers.add_parser("g10-assemble-us", help="Assemble a US G10 vintage and processed panel")
    g10_assemble_parser.add_argument("--vintage-date", required=True, help="Vintage date in YYYY-MM-DD form")
    g10_assemble_parser.add_argument("--vintage-month", help="FRED-MD/QD vintage month in YYYY-MM form; omit for current.csv")
    g10_assemble_parser.add_argument("--raw-root", default="data/raw", help="Raw source root")
    g10_assemble_parser.add_argument("--vintage-root", default="data/vintages", help="Vintage parquet root")
    g10_assemble_parser.add_argument("--processed-root", default="data/processed", help="Processed panel root")
    g10_assemble_parser.add_argument("--download", action="store_true", help="Download FRED-MD/QD raw files first")
    g10_assemble_parser.add_argument("--download-timeout", type=int, default=60, help="Per-request download timeout in seconds")
    g10_assemble_parser.add_argument("--download-retries", type=int, default=3, help="Download retry attempts")

    g10_coverage_parser = subparsers.add_parser("g10-check-coverage", help="Check country config against a vintage parquet")
    g10_coverage_parser.add_argument("--iso", default="US", help="ISO country code")
    g10_coverage_parser.add_argument("--vintage-date", required=True, help="Vintage date in YYYY-MM-DD form")
    g10_coverage_parser.add_argument("--vintage-root", default="data/vintages", help="Vintage parquet root")
    g10_coverage_parser.add_argument("--matrix-output", help="Optional CSV path for the coverage matrix")

    g10_smoke_parser = subparsers.add_parser("g10-dfm-smoke", help="Fit and persist a tiny G10 DFM smoke run")
    g10_smoke_parser.add_argument("--iso", default="US", help="ISO country code")
    g10_smoke_parser.add_argument("--vintage-date", required=True, help="Vintage date in YYYY-MM-DD form")
    g10_smoke_parser.add_argument("--processed-root", default="data/processed", help="Processed panel root")
    g10_smoke_parser.add_argument("--artifact-root", default="artifacts", help="Artifact root")
    g10_smoke_parser.add_argument("--maxiter", type=int, default=2, help="Small EM iteration cap for smoke runs")

    g10_publish_parser = subparsers.add_parser(
        "g10-publish-experimental",
        help="Publish an experimental G10 GDP output into the site contract",
    )
    g10_publish_parser.add_argument("--iso", default="US", help="ISO country code")
    g10_publish_parser.add_argument("--vintage-date", required=True, help="Vintage date in YYYY-MM-DD form")
    g10_publish_parser.add_argument("--processed-root", default="data/processed", help="Processed panel root")
    g10_publish_parser.add_argument("--vintage-root", default="data/vintages", help="Vintage parquet root")
    g10_publish_parser.add_argument("--artifact-root", default="artifacts", help="DFM artifact root")
    g10_publish_parser.add_argument("--publish-dir", default="site/data", help="Publish data root")
    g10_publish_parser.add_argument("--packs-dir", default="country_packs", help="Country packs directory")

    g10_run_experimental_parser = subparsers.add_parser(
        "g10-run-experimental-us",
        help="Assemble, smoke-fit, publish, and validate the experimental US G10 GDP output",
    )
    g10_run_experimental_parser.add_argument("--vintage-date", required=True, help="Vintage date in YYYY-MM-DD form")
    g10_run_experimental_parser.add_argument("--vintage-month", help="FRED-MD/QD vintage month in YYYY-MM form; omit for current.csv")
    g10_run_experimental_parser.add_argument("--raw-root", default="data/raw", help="Raw source root")
    g10_run_experimental_parser.add_argument("--vintage-root", default="data/vintages", help="Vintage parquet root")
    g10_run_experimental_parser.add_argument("--processed-root", default="data/processed", help="Processed panel root")
    g10_run_experimental_parser.add_argument("--artifact-root", default="artifacts", help="DFM artifact root")
    g10_run_experimental_parser.add_argument("--publish-dir", default="site/data", help="Publish data root")
    g10_run_experimental_parser.add_argument("--packs-dir", default="country_packs", help="Country packs directory")
    g10_run_experimental_parser.add_argument("--download", action="store_true", help="Download FRED-MD/QD raw files first")
    g10_run_experimental_parser.add_argument("--download-timeout", type=int, default=60, help="Per-request download timeout in seconds")
    g10_run_experimental_parser.add_argument("--download-retries", type=int, default=3, help="Download retry attempts")
    g10_run_experimental_parser.add_argument("--no-smoke", action="store_true", help="Skip the DFM smoke fit")

    g10_daily_parser = subparsers.add_parser("g10-daily", help="Future G10 daily DynamicFactorMQ loop")
    g10_daily_parser.add_argument("--iso", help="Optional ISO country code")

    g10_replay_parser = subparsers.add_parser("g10-replay", help="Future G10 historical replay")
    g10_replay_parser.add_argument("--iso", default="US", help="ISO country code")
    g10_replay_parser.add_argument("--start", help="Replay start vintage")
    g10_replay_parser.add_argument("--end", help="Replay end vintage")

    g10_refit_parser = subparsers.add_parser("g10-refit", help="Future G10 full DFM refit")
    g10_refit_parser.add_argument("--iso", default="US", help="ISO country code")

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

    if args.command == "g10-check-config":
        try:
            from nowcast.g10.config import load_country_config

            config = load_country_config(args.iso)
        except Exception as exc:
            print(f"g10 config check failed: {exc}", file=sys.stderr)
            return 1
        print(f"loaded {config['iso']} config with {len(config.get('targets', {}))} targets")
        return 0

    if args.command == "g10-assemble-us":
        try:
            from nowcast.g10.assemble import assemble_us_vintage
            from nowcast.g10.panel import build_processed_panel

            vintage_date = parse_as_of(args.vintage_date)
            if vintage_date is None:
                raise ValueError("--vintage-date is required")
            vintage_path = assemble_us_vintage(
                vintage_date,
                raw_root=Path(args.raw_root),
                vintage_root=Path(args.vintage_root),
                download=args.download,
                vintage_month=args.vintage_month,
                download_timeout=args.download_timeout,
                download_retries=args.download_retries,
            )
            panel_paths = build_processed_panel(
                "US",
                vintage_date,
                vintage_root=Path(args.vintage_root),
                processed_root=Path(args.processed_root),
            )
        except Exception as exc:
            print(f"g10 US assembly failed: {exc}", file=sys.stderr)
            return 1
        print(f"vintage {vintage_path}")
        print(f"monthly panel {panel_paths.monthly}")
        print(f"quarterly panel {panel_paths.quarterly}")
        return 0

    if args.command == "g10-check-coverage":
        try:
            from nowcast.g10.coverage import check_config_coverage, write_coverage_matrix

            vintage_date = parse_as_of(args.vintage_date)
            if vintage_date is None:
                raise ValueError("--vintage-date is required")
            coverage = check_config_coverage(
                args.iso,
                vintage_date,
                vintage_root=Path(args.vintage_root),
            )
            matrix_path = None
            if args.matrix_output:
                matrix_path = write_coverage_matrix(
                    args.iso,
                    vintage_date,
                    Path(args.matrix_output),
                    vintage_root=Path(args.vintage_root),
                )
        except Exception as exc:
            print(f"g10 coverage check failed: {exc}", file=sys.stderr)
            return 1
        print(
            f"{coverage.iso} coverage: {coverage.available_series} available series, "
            f"{len(coverage.missing_targets)} missing targets, "
            f"{len(coverage.missing_panel_series)} missing panel series, "
            f"ratio {coverage.coverage_ratio:.2%}, status {coverage.status()}"
        )
        if matrix_path is not None:
            print(f"coverage matrix {matrix_path}")
        if not coverage.ok:
            print(f"missing targets: {', '.join(coverage.missing_targets) or 'none'}")
            print(f"missing panel series: {', '.join(coverage.missing_panel_series) or 'none'}")
            return 1
        return 0

    if args.command == "g10-dfm-smoke":
        try:
            from nowcast.g10.smoke import run_dfm_smoke

            artifact = run_dfm_smoke(
                args.iso,
                args.vintage_date,
                processed_root=Path(args.processed_root),
                artifact_root=Path(args.artifact_root),
                maxiter=args.maxiter,
            )
        except Exception as exc:
            print(f"g10 DFM smoke failed: {exc}", file=sys.stderr)
            return 1
        print(f"smoke artifact {artifact.path}")
        return 0

    if args.command == "g10-publish-experimental":
        try:
            from nowcast.g10.experimental_publish import publish_experimental_g10_gdp

            vintage_date = parse_as_of(args.vintage_date)
            if vintage_date is None:
                raise ValueError("--vintage-date is required")
            result = publish_experimental_g10_gdp(
                args.iso,
                vintage_date=vintage_date,
                processed_root=Path(args.processed_root),
                vintage_root=Path(args.vintage_root),
                artifact_root=Path(args.artifact_root),
                publish_dir=Path(args.publish_dir),
                packs_dir=Path(args.packs_dir),
            )
        except Exception as exc:
            print(f"g10 experimental publish failed: {exc}", file=sys.stderr)
            return 1
        print(f"published {result.country_code}/{result.indicator_code} to {result.indicator_dir}")
        return 0

    if args.command == "g10-run-experimental-us":
        try:
            from nowcast.g10.assemble import assemble_us_vintage
            from nowcast.g10.experimental_publish import publish_experimental_g10_gdp
            from nowcast.g10.panel import build_processed_panel
            from nowcast.g10.smoke import run_dfm_smoke
            from nowcast.schemas import validate_publish_dir

            vintage_date = parse_as_of(args.vintage_date)
            if vintage_date is None:
                raise ValueError("--vintage-date is required")
            vintage_path = assemble_us_vintage(
                vintage_date,
                raw_root=Path(args.raw_root),
                vintage_root=Path(args.vintage_root),
                download=args.download,
                vintage_month=args.vintage_month,
                download_timeout=args.download_timeout,
                download_retries=args.download_retries,
            )
            panel_paths = build_processed_panel(
                "US",
                vintage_date,
                vintage_root=Path(args.vintage_root),
                processed_root=Path(args.processed_root),
            )
            smoke_artifact = None
            if not args.no_smoke:
                smoke_artifact = run_dfm_smoke(
                    "US",
                    vintage_date.isoformat(),
                    processed_root=Path(args.processed_root),
                    artifact_root=Path(args.artifact_root),
                    maxiter=2,
                )
            publish_result = publish_experimental_g10_gdp(
                "US",
                vintage_date=vintage_date,
                processed_root=Path(args.processed_root),
                vintage_root=Path(args.vintage_root),
                artifact_root=Path(args.artifact_root),
                publish_dir=Path(args.publish_dir),
                packs_dir=Path(args.packs_dir),
            )
            validation = validate_publish_dir(Path(args.publish_dir), countries=["us"])
            if not validation.ok:
                for error in validation.errors:
                    print(error, file=sys.stderr)
                return 1
        except Exception as exc:
            print(f"g10 experimental run failed: {exc}", file=sys.stderr)
            return 1
        print(f"vintage {vintage_path}")
        print(f"monthly panel {panel_paths.monthly}")
        print(f"quarterly panel {panel_paths.quarterly}")
        print(f"smoke artifact {smoke_artifact.path if smoke_artifact is not None else 'skipped'}")
        print(f"published {publish_result.country_code}/{publish_result.indicator_code} to {publish_result.indicator_dir}")
        latest = json.loads((publish_result.indicator_dir / "latest.json").read_text(encoding="utf-8"))
        summary = json.loads((publish_result.indicator_dir / "g10_experimental_summary.json").read_text(encoding="utf-8"))
        print(
            "estimate "
            f"{latest['estimate_value']} {latest['unit']} "
            f"(prior {latest['prior_estimate_value']}, delta {latest['delta_vs_prior']}, method {summary['method']})"
        )
        print("validation ok")
        return 0

    if args.command in {"g10-daily", "g10-replay", "g10-refit"}:
        print(
            f"{args.command} is scaffolded but not implemented yet; see docs/plan.md milestones M4-M5.",
            file=sys.stderr,
        )
        return 2

    parser.error(f"unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
