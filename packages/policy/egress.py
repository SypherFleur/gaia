from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DataEgressPolicy:
    allow_public_data_egress: bool = True
    allow_private_text_egress: bool = True
    allow_private_image_egress: bool = True
    allow_private_document_egress: bool = True
    allow_exact_location_egress: bool = True

    @classmethod
    def sovereign_default(cls) -> "DataEgressPolicy":
        return cls(
            allow_public_data_egress=True,
            allow_private_text_egress=False,
            allow_private_image_egress=False,
            allow_private_document_egress=False,
            allow_exact_location_egress=False,
        )

