"""Plain Python entry, no Functions Core Tools required."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from functions.publish.function_app import publish

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=ROOT / "fixtures/study_result.json")
    p.add_argument("--out", type=Path, default=ROOT / "out/published.json")
    a = p.parse_args()
    try:
        publish(json.loads(a.input.read_text(encoding="utf-8")), a.out)
        print(a.out)
    except (OSError, ValueError, TypeError) as exc:
        p.exit(1, f"Publish failed: {exc}\n")
