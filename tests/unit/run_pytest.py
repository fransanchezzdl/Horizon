#!/usr/bin/env python3
"""Runner de tests unitarios con spinner en consola."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_tool_with_fallback.py"),
        "pytest",
        "tests/unit",
        "-q",
    ]
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
