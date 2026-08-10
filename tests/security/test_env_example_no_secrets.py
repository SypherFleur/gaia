from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class EnvExampleSecretsTest(unittest.TestCase):
    def test_secret_like_values_are_blank(self) -> None:
        for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            if key.endswith(("SECRET", "API_KEY", "TOKEN")):
                self.assertEqual(value, "", f"{key} must be blank in .env.example")


if __name__ == "__main__":
    unittest.main()

