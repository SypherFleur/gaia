from __future__ import annotations

import os
import unittest


@unittest.skipUnless(
    os.environ.get("GAIA_RUN_CALENDAR_SMOKE") == "1" and os.environ.get("GOOGLE_CALENDAR_TEST_CALENDAR_ID"),
    "set GAIA_RUN_CALENDAR_SMOKE=1 and GOOGLE_CALENDAR_TEST_CALENDAR_ID for live Google Calendar smoke",
)
class GoogleCalendarSmokeTest(unittest.TestCase):
    def test_live_google_calendar_smoke_requires_explicit_oauth_configuration(self) -> None:
        self.skipTest("Live Google Calendar OAuth credentials are not configured in Phase 9.")


if __name__ == "__main__":
    unittest.main()
