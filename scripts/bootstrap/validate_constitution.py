from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "GAIA_MASTER_BUILD_PLAN.md",
    "COMPREHENSION_REPORT.md",
    "OPEN_QUESTIONS.md",
    "DECISIONS.md",
    ".env.example",
]

REQUIRED_ENV_FLAGS = {
    "GAIA_TOTAL_INITIAL_BUDGET_USD": "20.00",
    "GAIA_TARGET_DEVELOPMENT_CASH_SPEND_USD": "0.00",
    "GAIA_TARGET_COMMITTED_MONTHLY_INFRASTRUCTURE_USD": "0.00",
    "GAIA_ALLOW_PAID_MODELS": "false",
    "GAIA_ALLOW_PAID_APIS": "false",
    "GAIA_ALLOW_AUTOMATIC_INFRASTRUCTURE_UPGRADE": "false",
    "GAIA_ALLOW_AUTOMATIC_OVERAGE_BILLING": "false",
    "GAIA_ALLOW_AUTOMATIC_STORAGE_UPGRADE": "false",
    "GAIA_PAID_MODEL_FALLBACK_ENABLED": "false",
    "GAIA_PAID_DATA_FALLBACK_ENABLED": "false",
}


def read_env_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def assert_required_files() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not (ROOT / path).exists():
            errors.append(f"Missing required file: {path}")
    return errors


def assert_financial_constitution(env_values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for key, expected in REQUIRED_ENV_FLAGS.items():
        actual = env_values.get(key)
        if actual != expected:
            errors.append(f"{key} must be {expected!r}, got {actual!r}")
    return errors


def assert_no_obvious_secrets(env_values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    secret_like_keys = [key for key in env_values if key.endswith(("SECRET", "API_KEY", "TOKEN"))]
    for key in secret_like_keys:
        if env_values[key]:
            errors.append(f"{key} must be blank in .env.example")
    return errors


def main() -> int:
    errors = assert_required_files()
    env_values = read_env_example()
    errors.extend(assert_financial_constitution(env_values))
    errors.extend(assert_no_obvious_secrets(env_values))

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("GAIA constitution check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

