from __future__ import annotations

import json
import unittest

from packages.model_gateway.validation import GuidancePlanValidationError, validate_guidance_plan_draft
from packages.provenance import unverifiable_prose_identifiers
from packages.research.validation import ResearchValidationError, validate_synthesis_draft


def guidance_plan(**overrides) -> str:
    draft = {
        "subject": "Tomato heat stress",
        "situation": "Sustained highs above 35C during fruit set.",
        "recommendations": [{"summary": "Shade during peak afternoon heat."}],
        "actions": [{"title": "Install shade cloth"}],
        "timing": [{"window": "next 7 days"}],
        "resources": [],
        "risks": [],
        "uncertainty": {"level": "moderate", "confidence": 0.6},
        "measurements_to_take": [],
        "follow_up": [],
    }
    draft.update(overrides)
    return json.dumps(draft)


def synthesis(**overrides) -> str:
    draft = {
        "question": "Does shading reduce tomato heat stress?",
        "summary": "Shading reduced canopy temperature in the retrieved trials.",
        "evidence_quality": "moderate",
        "uncertainty": {"level": "moderate"},
    }
    draft.update(overrides)
    return json.dumps(draft)


class ProseIdentifierScannerTest(unittest.TestCase):
    def test_finds_doi_in_narrative_text(self) -> None:
        payload = {"summary": "As shown in 10.1016/j.agee.2019.106703, yields fell."}
        self.assertEqual(unverifiable_prose_identifiers(payload, set()), ["10.1016/j.agee.2019.106703"])

    def test_accepts_identifier_backed_by_a_retrieved_work(self) -> None:
        payload = {"summary": "See doi:10.1016/j.agee.2019.106703 for the trial."}
        allowed = {"https://doi.org/10.1016/j.agee.2019.106703"}
        self.assertEqual(unverifiable_prose_identifiers(payload, allowed), [])

    def test_finds_pmid_and_pmcid_variants(self) -> None:
        payload = {"notes": ["PMID: 31452951", "see PMC6721104 for the dataset"]}
        found = unverifiable_prose_identifiers(payload, set())
        self.assertIn("pmid:31452951", found)
        self.assertIn("PMC6721104", found)

    def test_ordinary_prose_and_numbers_are_not_flagged(self) -> None:
        payload = {
            "summary": "Apply 10.5 kg per hectare on 2026-08-15; version 10.2 of the guide covers this.",
            "timing": [{"window": "10 to 14 days"}],
        }
        self.assertEqual(unverifiable_prose_identifiers(payload, set()), [])

    def test_trailing_punctuation_does_not_defeat_matching(self) -> None:
        payload = {"summary": "Reported in 10.1016/j.agee.2019.106703."}
        allowed = {"10.1016/j.agee.2019.106703"}
        self.assertEqual(unverifiable_prose_identifiers(payload, allowed), [])


class GuidancePlanProseCitationTest(unittest.TestCase):
    def test_clean_plan_still_validates(self) -> None:
        self.assertEqual(validate_guidance_plan_draft(guidance_plan())["subject"], "Tomato heat stress")

    def test_fabricated_doi_in_prose_is_rejected(self) -> None:
        content = guidance_plan(
            recommendations=[{"summary": "Shade cloth cut heat stress (see 10.1234/fabricated.study.2026)."}]
        )
        with self.assertRaises(GuidancePlanValidationError) as caught:
            validate_guidance_plan_draft(content)

        self.assertIn("prose", str(caught.exception))

    def test_fabricated_pmid_in_situation_is_rejected(self) -> None:
        content = guidance_plan(situation="Heat stress is documented in PMID: 12345678.")
        with self.assertRaises(GuidancePlanValidationError):
            validate_guidance_plan_draft(content)

    def test_structured_source_id_injection_still_rejected(self) -> None:
        content = guidance_plan(recommendations=[{"summary": "Shade", "source_record_ids": ["src-made-up"]}])
        with self.assertRaises(GuidancePlanValidationError):
            validate_guidance_plan_draft(content)


class SynthesisProseCitationTest(unittest.TestCase):
    def test_clean_synthesis_still_validates(self) -> None:
        draft = validate_synthesis_draft(synthesis(), allowed_work_ids={"europepmc:1"})
        self.assertEqual(draft["evidence_quality"], "moderate")

    def test_fabricated_doi_in_summary_is_rejected(self) -> None:
        content = synthesis(summary="Shading helped, per 10.9999/not-a-real-doi.")
        with self.assertRaises(ResearchValidationError) as caught:
            validate_synthesis_draft(content, allowed_work_ids={"europepmc:1"})

        self.assertIn("prose", str(caught.exception))

    def test_identifier_matching_a_retrieved_work_is_allowed(self) -> None:
        content = synthesis(summary="Shading helped, per 10.1016/j.agee.2019.106703.")
        draft = validate_synthesis_draft(content, allowed_work_ids={"10.1016/j.agee.2019.106703"})

        self.assertTrue(draft["summary"])


if __name__ == "__main__":
    unittest.main()
