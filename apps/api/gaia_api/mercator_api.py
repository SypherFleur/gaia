from __future__ import annotations

from dataclasses import asdict

from packages.mercator import MercatorContextProvider
from packages.tools import ToolExecutionContext


async def get_production(
    mercator: MercatorContextProvider,
    context: ToolExecutionContext,
    *,
    commodity: str,
    geography: dict,
    location_id: str | None = None,
    crop_or_taxon: dict | None = None,
) -> dict:
    result = await mercator.build_context(context, commodity=commodity, geography=geography, location_id=location_id, crop_or_taxon=crop_or_taxon)
    return {"production_statistics": result.mercator_context.production_statistics, "source_record_ids": result.mercator_context.source_record_ids}


async def get_markets(
    mercator: MercatorContextProvider,
    context: ToolExecutionContext,
    *,
    commodity: str,
    geography: dict,
    market_region: str | None = None,
) -> dict:
    result = await mercator.build_context(context, commodity=commodity, geography=geography, market_region=market_region)
    return {"market_reports": result.mercator_context.market_reports, "price_observations": result.mercator_context.price_observations}


async def get_prices(
    mercator: MercatorContextProvider,
    context: ToolExecutionContext,
    *,
    commodity: str,
    geography: dict,
    market_region: str | None = None,
) -> dict:
    result = await mercator.build_context(context, commodity=commodity, geography=geography, market_region=market_region)
    return {"price_observations": result.mercator_context.price_observations, "freshness": result.mercator_context.freshness}


async def get_region(
    mercator: MercatorContextProvider,
    context: ToolExecutionContext,
    *,
    commodity: str,
    geography: dict,
) -> dict:
    result = await mercator.build_context(context, commodity=commodity, geography=geography)
    return {"regional_economic_context": result.mercator_context.regional_economic_context}


async def get_supply_chain(
    mercator: MercatorContextProvider,
    context: ToolExecutionContext,
    *,
    commodity: str,
    geography: dict,
) -> dict:
    result = await mercator.build_context(context, commodity=commodity, geography=geography)
    return {"supply_chain_context": result.mercator_context.supply_chain_context}


async def post_economics_context(
    mercator: MercatorContextProvider,
    context: ToolExecutionContext,
    *,
    commodity: str,
    geography: dict,
    location_id: str | None = None,
    crop_or_taxon: dict | None = None,
    market_region: str | None = None,
) -> dict:
    result = await mercator.build_context(
        context,
        commodity=commodity,
        geography=geography,
        location_id=location_id,
        crop_or_taxon=crop_or_taxon,
        market_region=market_region,
    )
    return asdict(result.mercator_context)

