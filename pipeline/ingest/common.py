from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable
from typing import TypeVar

import requests


T = TypeVar("T")


def configure_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("macro_data_store")


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--dry-run", action="store_true", help="Check connectivity without writing downloads")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    logger: logging.Logger | None = None,
    label: str = "request",
) -> T:
    if logger is None:
        logger = logging.getLogger("macro_data_store")
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in {400, 401, 403, 404}:
                raise
            last_error = exc
        except requests.RequestException as exc:
            last_error = exc
        if logger:
            logger.warning("%s failed on attempt %s/%s: %s", label, attempt, attempts, last_error)
        if attempt < attempts:
            time.sleep(base_delay * (2 ** (attempt - 1)))
    assert last_error is not None
    raise last_error
