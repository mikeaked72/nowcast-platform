"""G10 mixed-frequency dynamic-factor scaffolding.

This package is the bridge between the new G10 DynamicFactorMQ specification and
the existing static-site publishing pipeline. It deliberately keeps model/data
objects separate from the frontend output contract.
"""

from __future__ import annotations

G10_COUNTRIES = ("US", "CA", "UK", "DE", "FR", "IT", "JP", "CH", "SE", "NL", "BE")

