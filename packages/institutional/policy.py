from __future__ import annotations

from dataclasses import asdict

from packages.domain import OrganizationPolicy
from packages.policy import DataEgressPolicy


def sovereign_policy(organization_id: str) -> OrganizationPolicy:
    egress = asdict(DataEgressPolicy.sovereign_default())
    return OrganizationPolicy(
        organization_id=organization_id,
        deployment_mode="sovereign",
        location_precision_default="1km",
        telemetry_policy="DISABLED",
        model_policy={
            "allowed_model_providers": ["ollama-local", "llama-cpp-local"],
            "remote_models_allowed": False,
            "local_models_required": True,
        },
        tool_policy={"allowed_provider_ids": ["nws", "nasa-power", "usda-nrcs-sda", "usgs-water", "usda-nass", "usda-ams", "gbif", "europe-pmc", "fixture-calendar"]},
        egress_policy=egress,
        export_policy={"formats": ["json", "csv"], "include_secrets": False},
        data_sharing_policy={"public_sources_shareable": True, "private_annotations_shareable": False},
        retention_policy={
            "conversation_retention_days": 365,
            "media_retention_days": 365,
            "research_run_retention": "policy_controlled",
            "audit_retention": "policy_controlled",
            "deleted_data_grace_period": "policy_controlled",
        },
    )


def institution_policy(organization_id: str) -> OrganizationPolicy:
    return OrganizationPolicy(
        organization_id=organization_id,
        deployment_mode="institution",
        telemetry_policy="LOCAL_ONLY",
        model_policy={"allowed_model_providers": ["ollama-local"], "remote_models_allowed": False},
        tool_policy={"allowed_provider_ids": ["nws", "nasa-power", "usda-nass", "usda-ams", "europe-pmc", "gbif"]},
        egress_policy={"allow_private_document_egress": False, "allow_external_model_egress": False},
        export_policy={"formats": ["json", "csv"], "include_secrets": False},
        data_sharing_policy={"public_sources_shareable": True, "private_annotations_shareable": False},
        retention_policy={"research_run_retention": "institution_policy"},
    )


def telemetry_remote_allowed(policy: dict | None) -> bool:
    return bool(policy and policy.get("telemetry_policy") not in {"DISABLED", "LOCAL_ONLY"})

