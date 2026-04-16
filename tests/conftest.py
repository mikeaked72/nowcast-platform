from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """Workspace-local replacement for pytest's tmp_path on locked-down Windows.

    The desktop environment can deny access to directories created under the
    default pytest temp root. A per-test workspace path keeps tests deterministic
    and avoids touching user temp ACLs.
    """

    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.nodeid)[:90]
    path = Path("tmp") / "test-runs" / f"{name}_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path

