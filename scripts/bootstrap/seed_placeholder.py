from __future__ import annotations

from apps.api.gaia_api.runtime import create_runtime, seed_demo


def main() -> int:
    runtime = create_runtime()
    try:
        print(seed_demo(runtime))
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
