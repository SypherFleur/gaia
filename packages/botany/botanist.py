from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from packages.botany.tools import GBIFTaxonomyTool, GenesysGermplasmTool
from packages.domain import Observation, PlantEntity, PlantProfile, SourceRecord, UserPlant
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest, ToolResult


JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class TaxonLookupResult:
    status: str
    plant_entity: PlantEntity | None
    data: JsonDict
    source_record_ids: list[str]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class BotanistContext:
    user_plant: JsonDict
    plant_entity: JsonDict
    cultivar: str | None
    plant_profile: JsonDict | None
    taxonomy_sources: list[str]
    relevant_germplasm: list[JsonDict]
    recent_observations: list[JsonDict]
    model_run_count: int = 0

    def to_dict(self) -> JsonDict:
        return asdict(self)


class BotanistService:
    def __init__(
        self,
        repository: GaiaRepository,
        tool_gateway: ToolGateway,
        taxonomy_tool: GBIFTaxonomyTool,
        germplasm_tool: GenesysGermplasmTool,
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.taxonomy_tool = taxonomy_tool
        self.germplasm_tool = germplasm_tool

    async def resolve_taxon(self, context: ToolExecutionContext, query: str) -> TaxonLookupResult:
        result = await self.tool_gateway.execute(
            self.taxonomy_tool,
            context,
            ToolRequest(
                payload={"query": query},
                cache_key=f"gbif:taxon:{query.strip().lower()}",
                cache_ttl_seconds=86400 * 90,
                stale_if_error_seconds=86400 * 365,
                allow_stale_cache=True,
                estimated_cost_usd=0.0,
            ),
        )
        source_record_ids = self._persist_sources(context.organization_id, result.provenance)
        data = result.data
        if result.status in {"AMBIGUOUS", "UNRESOLVED", "PROVIDER_ERROR", "denied", "failed"}:
            return TaxonLookupResult(result.status, None, data, source_record_ids, result.warnings)
        canonical_taxon_id = data.get("canonical_taxon_id")
        plant_entity = None
        if canonical_taxon_id:
            existing = self.repository.find_plant_entity_by_taxon_id(canonical_taxon_id)
            if existing is not None:
                plant_entity = _plant_entity_from_record(existing)
        if plant_entity is None:
            plant_entity = PlantEntity(
                scientific_name=data.get("accepted_scientific_name") or data.get("matched_name") or query,
                canonical_taxon_id=canonical_taxon_id,
                kingdom=data.get("kingdom"),
                common_names=data.get("common_names", []),
                family=data.get("family"),
                genus=data.get("genus"),
                species=data.get("species"),
                crop_group=_crop_group_for(data),
                edible_classification=_edible_classification_for(data),
                synonyms=data.get("synonyms", []),
                external_source_ids=data.get("external_source_ids", {}),
                canonical_name_source_record_id=source_record_ids[0] if source_record_ids else None,
                source_ids=source_record_ids,
            )
            self.repository.create_plant_entity(plant_entity)
        return TaxonLookupResult(result.status, plant_entity, data, source_record_ids, result.warnings)

    async def search_germplasm(self, context: ToolExecutionContext, query: str, *, limit: int = 10) -> ToolResult:
        result = await self.tool_gateway.execute(
            self.germplasm_tool,
            context,
            ToolRequest(
                payload={"query": query, "limit": limit},
                cache_key=f"genesys:search:{query.strip().lower()}:{limit}",
                cache_ttl_seconds=86400 * 14,
                stale_if_error_seconds=86400 * 90,
                allow_stale_cache=True,
                estimated_cost_usd=0.0,
            ),
        )
        self._persist_sources(context.organization_id, result.provenance)
        return result

    def build_plant_profile(
        self,
        organization_id: str,
        plant_entity: PlantEntity,
        *,
        extra_conflicts: list[JsonDict] | None = None,
    ) -> PlantProfile:
        source_ids = plant_entity.source_ids
        field_provenance = {
            "scientific_name": _field_provenance(plant_entity.scientific_name, plant_entity.canonical_name_source_record_id, "gbif"),
            "family": _field_provenance(plant_entity.family, plant_entity.canonical_name_source_record_id, "gbif"),
            "genus": _field_provenance(plant_entity.genus, plant_entity.canonical_name_source_record_id, "gbif"),
            "species": _field_provenance(plant_entity.species, plant_entity.canonical_name_source_record_id, "gbif"),
            "common_names": _field_provenance(plant_entity.common_names, plant_entity.canonical_name_source_record_id, "gbif"),
        }
        known = sum(1 for value in [plant_entity.scientific_name, plant_entity.family, plant_entity.genus, plant_entity.species] if value)
        profile = PlantProfile(
            organization_id=organization_id,
            plant_entity_id=plant_entity.id,
            taxonomy={
                "canonical_taxon_id": plant_entity.canonical_taxon_id,
                "scientific_name": plant_entity.scientific_name,
                "kingdom": plant_entity.kingdom,
                "family": plant_entity.family,
                "genus": plant_entity.genus,
                "species": plant_entity.species,
                "synonyms": plant_entity.synonyms,
            },
            common_names=plant_entity.common_names,
            crop_group=plant_entity.crop_group,
            field_provenance=field_provenance,
            conflicts=extra_conflicts or [],
            source_record_ids=source_ids,
            confidence={"taxonomy": "source-backed", "traits": "mostly unknown"},
            completeness=known / 8.0,
        )
        self.repository.create_plant_profile(profile)
        return profile

    async def build_context(self, context: ToolExecutionContext, user_plant_id: str, *, germplasm_query: str | None = None) -> BotanistContext:
        user_plant = self.repository.get_user_plant(context.organization_id, user_plant_id)
        if user_plant is None:
            raise PermissionError("UserPlant is missing or inaccessible")
        plant_entity = self.repository.get_plant_entity(user_plant["plant_entity_id"])
        if plant_entity is None:
            raise PermissionError("PlantEntity is missing or inaccessible")
        profile = self.repository.get_latest_plant_profile(context.organization_id, plant_entity["id"])
        observations = self.repository.list_observations(context.organization_id, user_plant_id)[:10]
        germplasm = []
        if germplasm_query:
            result = await self.search_germplasm(context, germplasm_query)
            germplasm = result.data.get("accessions", [])
        return BotanistContext(
            user_plant=user_plant,
            plant_entity=plant_entity,
            cultivar=user_plant.get("cultivar"),
            plant_profile=profile,
            taxonomy_sources=plant_entity.get("source_ids", []),
            relevant_germplasm=germplasm,
            recent_observations=observations,
            model_run_count=0,
        )

    def _persist_sources(self, organization_id: str, provenance_records: list[ProvenanceRecord]) -> list[str]:
        source_ids = []
        for provenance in provenance_records:
            source = SourceRecord(
                organization_id=organization_id,
                provider=provenance.provider,
                source_type="botanical",
                canonical_url=provenance.canonical_url,
                external_record_id=provenance.external_record_id,
                title=provenance.external_record_id or provenance.provider,
                authority=provenance.authority,
                retrieved_at=provenance.retrieved_at,
                observed_at=provenance.observed_at,
                valid_from=provenance.valid_at,
                valid_to=None,
                license=provenance.license,
                attribution=provenance.attribution,
                content_hash=provenance.content_hash,
                raw_snapshot_reference=None,
            )
            self.repository.create_source_record(source)
            source_ids.append(source.id)
        return source_ids


def _plant_entity_from_record(record: JsonDict) -> PlantEntity:
    return PlantEntity(
        id=record["id"],
        scientific_name=record["scientific_name"],
        canonical_taxon_id=record["canonical_taxon_id"],
        kingdom=record.get("kingdom"),
        common_names=record.get("common_names", []),
        family=record.get("family"),
        genus=record.get("genus"),
        species=record.get("species"),
        subspecies=record.get("subspecies"),
        cultivar_optional=record.get("cultivar_optional"),
        crop_group=record.get("crop_group"),
        edible_classification=record.get("edible_classification"),
        native_status=record.get("native_status"),
        introduced_status=record.get("introduced_status"),
        synonyms=record.get("synonyms", []),
        external_source_ids=record.get("external_source_ids", {}),
        canonical_name_source_record_id=record.get("canonical_name_source_record_id"),
        source_ids=record.get("source_ids", []),
    )


def _field_provenance(value: Any, source_record_id: str | None, provider: str) -> JsonDict:
    return {"value": value, "source_record_id": source_record_id, "provider": provider}


def _crop_group_for(data: JsonDict) -> str | None:
    names = {name.lower() for name in data.get("common_names", [])}
    if "tomato" in names:
        return "vegetable"
    return None


def _edible_classification_for(data: JsonDict) -> str | None:
    names = {name.lower() for name in data.get("common_names", [])}
    if "tomato" in names:
        return "edible"
    return None
