from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowcast.schemas import validate_publish_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate published nowcast site payloads.")
    country_group = parser.add_mutually_exclusive_group()
    country_group.add_argument("--country", help="Single country code")
    country_group.add_argument("--countries", help="Comma-separated country codes")
    parser.add_argument("--publish-dir", default="site/data", help="Publish data root or country directory")
    args = parser.parse_args()

    countries = None
    if args.country:
        countries = [args.country]
    elif args.countries:
        countries = [country.strip() for country in args.countries.split(",") if country.strip()]

    result = validate_publish_dir(Path(args.publish_dir), countries=countries)
    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
