from __future__ import annotations

import unittest
from datetime import date

from packages.orchestration.orchestrator import derive_season_window


class ChatSeasonWindowTest(unittest.TestCase):
    def test_no_hint_defaults_to_ninety_days_from_today(self) -> None:
        start, end = derive_season_window("Plan my garden.", date(2026, 8, 15))
        self.assertEqual(start, "2026-08-15")
        self.assertEqual(end, "2026-11-13")

    def test_spring_request_in_august_targets_next_march(self) -> None:
        start, end = derive_season_window("Plan my spring garden.", date(2026, 8, 15))
        self.assertEqual(start, "2027-03-01")
        self.assertEqual(end, "2027-05-31")

    def test_fall_request_in_august_starts_september_first(self) -> None:
        start, end = derive_season_window("Plan my fall garden.", date(2026, 8, 15))
        self.assertEqual(start, "2026-09-01")
        self.assertEqual(end, "2026-11-30")

    def test_in_progress_season_starts_today_not_in_the_past(self) -> None:
        start, end = derive_season_window("Plan my fall garden.", date(2026, 10, 10))
        self.assertEqual(start, "2026-10-10")
        self.assertEqual(end, "2026-11-30")

    def test_winter_spans_the_year_boundary(self) -> None:
        start, end = derive_season_window("Plan my winter cover crops.", date(2026, 1, 15))
        self.assertEqual(start, "2026-01-15")
        self.assertEqual(end, "2026-02-28")

    def test_explicit_month_targets_next_occurrence(self) -> None:
        start, end = derive_season_window("Plan planting starting in March.", date(2026, 8, 15))
        self.assertEqual(start, "2027-03-01")
        self.assertEqual(end, "2027-05-31")

    def test_modal_may_is_not_treated_as_a_month(self) -> None:
        start, end = derive_season_window("What may I plant now?", date(2026, 8, 15))
        self.assertEqual(start, "2026-08-15")
        self.assertEqual(end, "2026-11-13")

    def test_earliest_upcoming_window_wins_when_multiple_are_named(self) -> None:
        start, end = derive_season_window("Plan fall and winter beds.", date(2026, 8, 15))
        self.assertEqual(start, "2026-09-01")
        self.assertEqual(end, "2026-11-30")


if __name__ == "__main__":
    unittest.main()
