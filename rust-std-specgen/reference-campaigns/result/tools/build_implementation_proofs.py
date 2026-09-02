#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import implementation

if __name__ == "__main__":
    print(json.dumps(implementation.generate(), sort_keys=True))

