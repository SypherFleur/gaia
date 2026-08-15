from __future__ import annotations

import unittest
from datetime import date, datetime

from packages.season.calculations import _FallbackUSTimezone, _nth_sunday, local_midday_iso


class FallbackTimezoneTest(unittest.TestCase):
    def test_second_sunday_in_march_and_first_in_november(self) -> None:
        self.assertEqual(_nth_sunday(2026, 3, 2), date(2026, 3, 8))
        self.assertEqual(_nth_sunday(2026, 11, 1), date(2026, 11, 1))

    def test_central_time_uses_standard_offset_in_winter(self) -> None:
        central = _FallbackUSTimezone("America/Chicago", -6, -5)
        offset = datetime(2026, 1, 15, 10, 0, tzinfo=central).utcoffset()

        self.assertEqual(offset.total_seconds() / 3600, -6)

    def test_central_time_uses_daylight_offset_in_summer(self) -> None:
        central = _FallbackUSTimezone("America/Chicago", -6, -5)
        offset = datetime(2026, 7, 15, 10, 0, tzinfo=central).utcoffset()

        self.assertEqual(offset.total_seconds() / 3600, -5)

    def test_transition_boundaries_are_respected(self) -> None:
        central = _FallbackUSTimezone("America/Chicago", -6, -5)
        before = datetime(2026, 3, 8, 1, 0, tzinfo=central).utcoffset().total_seconds() / 3600
        after = datetime(2026, 3, 8, 3, 0, tzinfo=central).utcoffset().total_seconds() / 3600

        self.assertEqual(before, -6)
        self.assertEqual(after, -5)

    def test_non_dst_zone_never_shifts(self) -> None:
        phoenix = _FallbackUSTimezone("America/Phoenix", -7, -7)
        winter = datetime(2026, 1, 15, 10, 0, tzinfo=phoenix).utcoffset().total_seconds() / 3600
        summer = datetime(2026, 7, 15, 10, 0, tzinfo=phoenix).utcoffset().total_seconds() / 3600

        self.assertEqual(winter, -7)
        self.assertEqual(summer, -7)

    def test_local_midday_matches_real_zoneinfo_across_dst(self) -> None:
        # Where tzdata is present this exercises ZoneInfo directly; the fallback
        # above is asserted to agree with these same offsets.
        self.assertTrue(local_midday_iso(date(2026, 1, 15), "America/Chicago").endswith("-06:00"))
        self.assertTrue(local_midday_iso(date(2026, 7, 15), "America/Chicago").endswith("-05:00"))


if __name__ == "__main__":
    unittest.main()
