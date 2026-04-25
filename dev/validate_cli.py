"""
dev/validate_cli.py — Pre-submission validation runner.

Delegates to dev/validate_env.py for all checks.

Usage (from repo root):
    python dev/validate_cli.py
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).resolve()
    repo_root = here.parent.parent
    result = subprocess.run(
        [sys.executable, str(here.parent / "validate_env.py")],
        cwd=repo_root,
    )
    sys.exit(result.returncode)
