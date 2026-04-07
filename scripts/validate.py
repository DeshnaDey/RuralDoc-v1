"""
scripts/validate.py — Pre-submission validation runner.

Delegates to rural_doc_env.validate for all checks.

Usage (from repo root):
    python scripts/validate.py
"""

import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "-m", "rural_doc_env.validate"],
        cwd=__file__.replace("/scripts/validate.py", ""),
    )
    sys.exit(result.returncode)
