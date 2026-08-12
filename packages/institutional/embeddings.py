from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EmbeddingProvider(Protocol):
    provider_id: str
    remote: bool

    async def embed(self, text: str) -> list[float]: ...


@dataclass(slots=True)
class FixtureEmbeddingProvider:
    provider_id: str = "fixture-local-embedding"
    remote: bool = False

    async def embed(self, text: str) -> list[float]:
        total = sum(ord(char) for char in text)
        return [float(total % 997), float(len(text)), float(len(set(text.lower())))]


@dataclass(slots=True)
class RemoteEmbeddingProviderStub:
    provider_id: str = "future-remote-embedding"
    remote: bool = True

    async def embed(self, text: str) -> list[float]:
        return [0.0]

