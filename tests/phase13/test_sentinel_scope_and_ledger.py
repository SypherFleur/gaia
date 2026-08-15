from __future__ import annotations

import unittest

from packages.audit import UsageEvent, UsageLedger
from packages.domain import Membership, Organization, User
from packages.persistence import GaiaRepository, connect_in_memory, initialize_schema
from packages.sentinel.engine import _scope_matches


class SentinelAnyScopeTest(unittest.TestCase):
    def test_any_state_scope_still_applies_county_narrowing(self) -> None:
        scope = {"state_code": "ANY", "counties": ["Broward"]}
        broward = {"country_code": "US", "state_code": "FL", "county_or_district": "Broward County"}
        travis = {"country_code": "US", "state_code": "TX", "county_or_district": "Travis County"}

        self.assertTrue(_scope_matches(scope, broward, {}, "origin"))
        self.assertFalse(_scope_matches(scope, travis, {}, "origin"))

    def test_any_state_scope_still_applies_quarantine_zone_narrowing(self) -> None:
        scope = {"state_code": "ANY", "quarantine_zone": "citrus greening"}
        inside = {"country_code": "US", "state_code": "TX", "quarantine_zones": ["Citrus Greening Quarantine Area"]}
        outside = {"country_code": "US", "state_code": "TX", "quarantine_zones": []}

        self.assertTrue(_scope_matches(scope, inside, {}, "origin"))
        self.assertFalse(_scope_matches(scope, outside, {}, "origin"))

    def test_any_state_scope_still_excludes_named_state(self) -> None:
        scope = {"state_code": "ANY", "exclude_state_code": "FL"}
        florida = {"country_code": "US", "state_code": "FL"}
        texas = {"country_code": "US", "state_code": "TX"}

        self.assertFalse(_scope_matches(scope, florida, {}, "origin"))
        self.assertTrue(_scope_matches(scope, texas, {}, "origin"))


class LedgerSpendScopingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_in_memory()
        initialize_schema(self.connection)
        self.repo = GaiaRepository(self.connection)
        self.ledger = UsageLedger(self.connection)
        self.org_a, self.user_a = self._tenant("alpha")
        self.org_b, self.user_b = self._tenant("beta")

    def tearDown(self) -> None:
        self.connection.close()

    def _tenant(self, slug: str) -> tuple[str, str]:
        organization = self.repo.create_organization(Organization(name=slug, slug=f"ledger-{slug}"))
        user = self.repo.create_user(User(external_auth_id=f"dev:{slug}", display_name=slug))
        self.repo.create_membership(Membership(organization_id=organization.id, user_id=user.id, role="owner", permissions=["tool.read"]))
        return organization.id, user.id

    def test_estimated_external_spend_scopes_by_organization_when_asked(self) -> None:
        self.ledger.record(UsageEvent(organization_id=self.org_a, user_id=self.user_a, provider_id="p", request_id="r1", status="success", estimated_cost_usd=1.25))
        self.ledger.record(UsageEvent(organization_id=self.org_b, user_id=self.user_b, provider_id="p", request_id="r2", status="success", estimated_cost_usd=0.50))

        self.assertEqual(self.ledger.estimated_external_spend(self.org_a), 1.25)
        self.assertEqual(self.ledger.estimated_external_spend(self.org_b), 0.50)
        self.assertEqual(self.ledger.estimated_external_spend(), 1.75)


if __name__ == "__main__":
    unittest.main()
