from __future__ import annotations

from typing import Any


JsonDict = dict[str, Any]


class MercatorValidationError(ValueError):
    pass


def validate_economic_synthesis(draft: JsonDict, trusted_context: JsonDict) -> JsonDict:
    if not isinstance(draft, dict):
        raise MercatorValidationError("economic_synthesis_not_object")
    fabricated = _find_fabricated_numbers(draft, trusted_context)
    if fabricated:
        raise MercatorValidationError("model_generated_economic_numbers_rejected")
    if _mentions_trading_signal(draft):
        raise MercatorValidationError("trading_or_forecast_signal_rejected")
    return draft


def assert_observation_not_live_logistics(record: JsonDict) -> None:
    if record.get("data_class") == "STRUCTURAL_SUPPLY_CHAIN" and str(record.get("freshness", "")).lower() in {"current", "live", "realtime"}:
        raise MercatorValidationError("structural_supply_chain_cannot_be_live_logistics")


def _find_fabricated_numbers(draft: JsonDict, trusted_context: JsonDict) -> list[str]:
    trusted = set(_collect_numbers(trusted_context))
    return [number for number in _collect_numbers(draft) if number not in trusted]


def _collect_numbers(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for nested in value.values():
            found.extend(_collect_numbers(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_collect_numbers(nested))
    elif isinstance(value, (int, float)):
        found.append(str(float(value)))
    return found


def _mentions_trading_signal(value: Any) -> bool:
    text = str(value).lower()
    return any(term in text for term in ["futures trade", "buy signal", "sell signal", "guaranteed profit"])

