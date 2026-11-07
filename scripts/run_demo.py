"""Run from the project root: python scripts/run_demo.py"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chembridge import convert_file

destination = ROOT / "runs" / datetime.now().strftime("demo_%Y%m%d_%H%M%S_%f")
jobs = [("molecules.csv", 5, 0), ("mixed_invalid.csv", 1, 2), ("misnamed.csv", 1, 0)]
summary = []
for name, expected_ok, expected_failed in jobs:
    result = convert_file(ROOT / "examples" / name, destination / Path(name).stem)
    assert result["converted_records"] == expected_ok
    assert result["failed_records"] == expected_failed
    summary.append({"input": name, "detected": result["detection"]["format"],
                    "converted": result["converted_records"], "failed": result["failed_records"],
                    "status": result["status"]})
print(json.dumps(summary, indent=2))
print("Open this directory:", destination)
