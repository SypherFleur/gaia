from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_FILE = ROOT / "data" / "evals" / "phase0_smoke_prompts.txt"


def main() -> int:
    prompts = [line for line in SMOKE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(prompts) < 5:
        print("FAIL: Phase 0 eval smoke fixture must contain at least five prompts.")
        return 1
    print(f"GAIA eval smoke fixture contains {len(prompts)} prompts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
