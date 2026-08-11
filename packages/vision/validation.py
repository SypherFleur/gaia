from __future__ import annotations

from typing import Any


class VisionValidationError(ValueError):
    pass


CONFIRMED_TERMS = [
    "confirmed",
    "definitive",
    "diagnosed",
    "definitely",
    "guaranteed",
]


def validate_visual_response(observations: list[dict[str, Any]], hypotheses: list[dict[str, Any]]) -> None:
    if not isinstance(observations, list) or not isinstance(hypotheses, list):
        raise VisionValidationError("vision_output_not_structured")
    for observation in observations:
        text = " ".join(str(value) for value in observation.values()).lower()
        if any(term in text for term in CONFIRMED_TERMS):
            raise VisionValidationError("visual_observation_contains_diagnostic_language")
    for hypothesis in hypotheses:
        status = str(hypothesis.get("status", "hypothesis")).lower()
        text = " ".join(str(value) for value in hypothesis.values()).lower()
        if status not in {"hypothesis", "possible", "candidate"}:
            raise VisionValidationError("visual_hypothesis_status_not_cautious")
        if any(term in text for term in CONFIRMED_TERMS):
            raise VisionValidationError("visual_hypothesis_overclaims_diagnosis")
