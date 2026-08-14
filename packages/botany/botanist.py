from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from packages.botany.tools import GBIFTaxonomyTool, GenesysGermplasmTool
from packages.domain import Observation, PlantEntity, PlantProfile, SourceRecord, UserPlant
from packages.persistence import GaiaRepository
from packages.provenance import ProvenanceRecord
from packages.tools import GaiaTool, ToolExecutionContext, ToolGateway, ToolRequest, ToolResult


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
    recent_visual_analyses: list[JsonDict]
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
        taxonomy_supplement_tools: list[GaiaTool] | None = None,
    ) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.taxonomy_tool = taxonomy_tool
        self.germplasm_tool = germplasm_tool
        self.taxonomy_supplement_tools = taxonomy_supplement_tools or []
        self._taxon_global_context: dict[str, JsonDict] = {}

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
        status = result.status
        warnings = list(result.warnings)
        source_provider = _result_provider(result, self.taxonomy_tool.provider_id)
        for supplement_tool in self.taxonomy_supplement_tools:
            supplemental = await self.tool_gateway.execute(
                supplement_tool,
                context,
                ToolRequest(
                    payload={"query": query},
                    cache_key=f"{supplement_tool.provider_id}:taxon:{query.strip().lower()}",
                    cache_ttl_seconds=86400 * 90,
                    stale_if_error_seconds=86400 * 365,
                    allow_stale_cache=True,
                    estimated_cost_usd=0.0,
                ),
            )
            supplemental_source_ids = self._persist_sources(context.organization_id, supplemental.provenance)
            if supplemental.status not in {"denied", "failed", "fail_closed", "PROVIDER_ERROR", "UNRESOLVED"}:
                data = _merge_taxonomy_data(data, supplemental.data)
                source_record_ids.extend(supplemental_source_ids)
                if status in {"AMBIGUOUS", "UNRESOLVED", "PROVIDER_ERROR", "denied", "failed"}:
                    status = supplemental.status
                    source_provider = _result_provider(supplemental, supplement_tool.provider_id)
            warnings.extend(supplemental.warnings)
        canonical_taxon_id = data.get("canonical_taxon_id")
        if canonical_taxon_id:
            self._taxon_global_context[canonical_taxon_id] = _global_context_from_taxonomy_data(data, source_record_ids, source_provider)
        if status in {"AMBIGUOUS", "UNRESOLVED", "PROVIDER_ERROR", "denied", "failed"}:
            return TaxonLookupResult(status, None, data, source_record_ids, warnings)
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
                external_source_ids={**data.get("external_source_ids", {}), "_canonical_provider": source_provider},
                canonical_name_source_record_id=source_record_ids[0] if source_record_ids else None,
                source_ids=source_record_ids,
            )
            self.repository.create_plant_entity(plant_entity)
        return TaxonLookupResult(status, plant_entity, data, source_record_ids, warnings)

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
        germplasm_links: list[JsonDict] | None = None,
        extra_conflicts: list[JsonDict] | None = None,
    ) -> PlantProfile:
        source_ids = plant_entity.source_ids
        global_context = self._taxon_global_context.get(plant_entity.canonical_taxon_id or "", {})
        source_provider = global_context.get("source_provider") or plant_entity.external_source_ids.get("_canonical_provider") or "gbif"
        field_provenance = {
            "scientific_name": _field_provenance(plant_entity.scientific_name, plant_entity.canonical_name_source_record_id, source_provider),
            "family": _field_provenance(plant_entity.family, plant_entity.canonical_name_source_record_id, source_provider),
            "genus": _field_provenance(plant_entity.genus, plant_entity.canonical_name_source_record_id, source_provider),
            "species": _field_provenance(plant_entity.species, plant_entity.canonical_name_source_record_id, source_provider),
            "common_names": _field_provenance(plant_entity.common_names, plant_entity.canonical_name_source_record_id, source_provider),
        }
        for field_name in [
            "native_range",
            "introduced_range",
            "biomes",
            "ecoregions",
            "climate_associations",
            "crop_origin",
            "plant_traits",
            "agricultural_uses",
            "occurrence_sources",
            "research_sources",
        ]:
            if global_context.get(field_name):
                field_provenance[field_name] = _field_provenance(global_context[field_name], plant_entity.canonical_name_source_record_id, source_provider)
        traits = global_context.get("plant_traits", {})
        uses = global_context.get("agricultural_uses", {})
        climate = global_context.get("climate_associations", {})
        known = sum(
            1
            for value in [
                plant_entity.scientific_name,
                plant_entity.family,
                plant_entity.genus,
                plant_entity.species,
                global_context.get("native_range"),
                global_context.get("biomes"),
                climate,
                uses,
            ]
            if value
        )
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
            native_range=global_context.get("native_range", []),
            introduced_range=global_context.get("introduced_range", []),
            biomes=global_context.get("biomes", []),
            ecoregions=global_context.get("ecoregions", []),
            climate_associations=climate,
            crop_group=plant_entity.crop_group,
            crop_origin=global_context.get("crop_origin", {}),
            growth_habit=traits.get("growth_habit"),
            lifecycle=traits.get("lifecycle"),
            crop_use={"values": uses.get("crop_use", []), "source": source_provider} if uses.get("crop_use") else {},
            food_use={"values": uses.get("food_use", []), "source": source_provider} if uses.get("food_use") else {},
            forage_use={"values": uses.get("forage_use", []), "source": source_provider} if uses.get("forage_use") else {},
            ornamental_use={"values": uses.get("ornamental_use", []), "source": source_provider} if uses.get("ornamental_use") else {},
            temperature_associations={"value": climate.get("temperature"), "source": source_provider} if climate.get("temperature") else {},
            water_associations={"value": climate.get("moisture"), "source": source_provider} if climate.get("moisture") else {},
            temperature_context={"association": climate.get("temperature"), "source": source_provider} if climate.get("temperature") else {},
            water_context={"association": climate.get("moisture"), "source": source_provider} if climate.get("moisture") else {},
            germplasm_links=germplasm_links or [],
            occurrence_sources=global_context.get("occurrence_sources", []),
            research_sources=global_context.get("research_sources", []),
            field_provenance=field_provenance,
            conflicts=extra_conflicts or [],
            source_record_ids=source_ids,
            confidence={"taxonomy": "source-backed", "global_context": "source-backed when populated", "traits": "unknown unless populated by provider fixture"},
            completeness=known / 12.0,
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
        visual_analyses = self.repository.list_visual_analyses_for_plant(context.organization_id, user_plant_id)[:5]
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
            recent_visual_analyses=visual_analyses,
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


def _global_context_from_taxonomy_data(data: JsonDict, source_record_ids: list[str], source_provider: str) -> JsonDict:
    context = {
        "native_range": data.get("native_range", []),
        "introduced_range": data.get("introduced_range", []),
        "biomes": data.get("biomes", []),
        "ecoregions": data.get("ecoregions", []),
        "climate_associations": data.get("climate_associations", {}),
        "crop_origin": data.get("crop_origin", {}),
        "plant_traits": data.get("plant_traits", {}),
        "agricultural_uses": data.get("agricultural_uses", {}),
        "occurrence_sources": data.get("occurrence_sources", []),
        "research_sources": data.get("research_sources", []),
        "source_provider": source_provider,
    }
    if any(context.values()):
        context["source_record_ids"] = source_record_ids
    return context


def _result_provider(result: ToolResult, fallback: str | None) -> str:
    if result.provenance:
        return result.provenance[0].provider
    return fallback or "unknown"


def _merge_taxonomy_data(primary: JsonDict, supplemental: JsonDict) -> JsonDict:
    merged = dict(primary)
    for key in [
        "native_range",
        "introduced_range",
        "biomes",
        "ecoregions",
        "occurrence_sources",
        "research_sources",
        "synonyms",
        "common_names",
    ]:
        merged[key] = _merge_list(merged.get(key, []), supplemental.get(key, []))
    for key in ["climate_associations", "crop_origin", "plant_traits", "agricultural_uses", "external_source_ids"]:
        merged[key] = {**supplemental.get(key, {}), **merged.get(key, {})}
    if not merged.get("canonical_taxon_id"):
        for key, value in supplemental.items():
            if not merged.get(key):
                merged[key] = value
    return merged


def _merge_list(left: list, right: list) -> list:
    merged = []
    seen = set()
    for item in [*left, *right]:
        marker = repr(item)
        if marker in seen:
            continue
        seen.add(marker)
        merged.append(item)
    return merged


def _crop_group_for(data: JsonDict) -> str | None:
    names = {name.lower() for name in data.get("common_names", [])}
    if "tomato" in names:
        return "vegetable"
    if "cowpea" in names:
        return "pulse"
    return None


def _edible_classification_for(data: JsonDict) -> str | None:
    names = {name.lower() for name in data.get("common_names", [])}
    if "tomato" in names:
        return "edible"
    if "cowpea" in names or "black-eyed pea" in names:
        return "edible"
    return None
