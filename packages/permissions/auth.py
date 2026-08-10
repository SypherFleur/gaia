from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: str
    organization_id: str
    roles: tuple[str, ...]
    provider: str


class AuthProvider(Protocol):
    provider_id: str
    production_safe: bool

    def authenticate(self, subject: str) -> AuthenticatedPrincipal:
        """Return an authenticated principal or raise an auth-specific error."""


class DevelopmentIdentityProvider:
    provider_id = "development"
    production_safe = False

    def __init__(self, principals: dict[str, AuthenticatedPrincipal]) -> None:
        self._principals = principals

    def authenticate(self, subject: str) -> AuthenticatedPrincipal:
        try:
            return self._principals[subject]
        except KeyError as exc:
            raise PermissionError("Unknown development identity") from exc

