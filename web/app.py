from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR_STRING = str(ROOT_DIR)
if ROOT_DIR_STRING not in sys.path:
    sys.path.insert(0, ROOT_DIR_STRING)

from portal.app import main


if __name__ == "__main__":
    main()
