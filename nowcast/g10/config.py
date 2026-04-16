"""Load G10 model configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml_config(path: Path | str) -> dict[str, Any]:
    """Load a YAML config file.

    PyYAML is a declared project dependency, but this import stays local so
    non-config code remains importable in minimal test environments.
    """

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read G10 config files") from exc

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return payload


def load_country_config(iso: str, config_dir: Path | str = "config/countries") -> dict[str, Any]:
    path = Path(config_dir) / f"{iso.upper()}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"missing country config: {path}")
    payload = load_yaml_config(path)
    if payload.get("iso") != iso.upper():
        raise ValueError(f"{path}: iso must be {iso.upper()}")
    return payload

