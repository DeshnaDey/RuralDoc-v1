"""
scripts/validate.py — Pre-submission validation runner.

Delegates to env.validate for all checks.

Usage (from repo root):
    python scripts/validate.py
"""

import subprocess
import sys
import os

if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-m", "env.validate"],
        cwd=repo_root,
    )
    sys.exit(result.returncode)
