# CREATE A NEW FILE: C:\Endoapp3\run.py

#!/usr/bin/env python3
import sys
from pathlib import Path
import os

# Ensure console encoding can handle unicode output to avoid startup crashes
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Set up the Python import path
PROJECT_ROOT = Path(__file__).absolute().parent
SRC_DIR = PROJECT_ROOT / "src"

# Insert the src directory at the beginning of the path
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Now run the main module
from src.main import main

if __name__ == "__main__":
    main()
