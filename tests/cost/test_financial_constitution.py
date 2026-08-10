from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


class FinancialConstitutionTest(unittest.TestCase):
    def test_paid_usage_disabled_by_default(self) -> None:
        values = env_values()

        self.assertEqual(values["GAIA_TOTAL_INITIAL_BUDGET_USD"], "20.00")
        self.assertEqual(values["GAIA_TARGET_DEVELOPMENT_CASH_SPEND_USD"], "0.00")
        self.assertEqual(values["GAIA_TARGET_COMMITTED_MONTHLY_INFRASTRUCTURE_USD"], "0.00")
        self.assertEqual(values["GAIA_ALLOW_PAID_MODELS"], "false")
        self.assertEqual(values["GAIA_ALLOW_PAID_APIS"], "false")
        self.assertEqual(values["GAIA_ALLOW_AUTOMATIC_OVERAGE_BILLING"], "false")


if __name__ == "__main__":
    unittest.main()

