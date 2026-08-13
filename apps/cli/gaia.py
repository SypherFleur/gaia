from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from apps.api.gaia_api.runtime import DEFAULT_SQLITE_URL, ROOT, cost_status, create_runtime


JsonDict = dict[str, Any]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    try:
        result = args.handler(args)
    except Exception as exc:
        print_json({"status": "error", "error": exc.__class__.__name__, "message": str(exc)})
        return 1
    print_json(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gaia", description="GAIA local-first command line interface")
    parser.add_argument("--database", default=DEFAULT_SQLITE_URL, help="SQLite URL. Use sqlite:///:memory: for ephemeral fixture runs.")
    parser.add_argument("--sovereign", action="store_true", help="Use sovereign local policy defaults for the command runtime.")
    subcommands = parser.add_subparsers(dest="command")

    doctor = subcommands.add_parser("doctor", help="Check local safety, provider, Docker, and zero-spend posture.")
    doctor.set_defaults(handler=handle_doctor)

    cost = subcommands.add_parser("cost", help="Cost and spend controls.")
    cost_subcommands = cost.add_subparsers(dest="cost_command")
    cost_status_cmd = cost_subcommands.add_parser("status", help="Show cost status.")
    cost_status_cmd.set_defaults(handler=handle_cost_status)

    providers = subcommands.add_parser("providers", help="Provider registry inspection.")
    providers_subcommands = providers.add_subparsers(dest="providers_command")
    providers_list = providers_subcommands.add_parser("list", help="List configured providers.")
    providers_list.set_defaults(handler=handle_providers_list)

    eval_cmd = subcommands.add_parser("eval", help="Evaluation harness commands.")
    eval_subcommands = eval_cmd.add_subparsers(dest="eval_command")
    eval_run = eval_subcommands.add_parser("run", help="Run the smoke eval fixture check.")
    eval_run.set_defaults(handler=handle_eval_run)

    sentinel = subcommands.add_parser("sentinel", help="Sentinel regulatory checks.")
    sentinel_subcommands = sentinel.add_subparsers(dest="sentinel_command")
    movement = sentinel_subcommands.add_parser("check-movement", help="Run a deterministic fixture movement check.")
    movement.add_argument("--origin", help="Location alias such as tx-houston, fl-orlando, fl-broward, ga-atlanta, ca-los-angeles.")
    movement.add_argument("--destination", help="Location alias such as tx-hidalgo or fl-orlando.")
    movement.add_argument("--source-country")
    movement.add_argument("--destination-country")
    movement.add_argument("--species", required=True)
    movement.add_argument("--plant-part", default="unknown")
    movement.add_argument("--live-plant", action="store_true")
    movement.add_argument("--soil-attached", action="store_true")
    movement.add_argument("--purpose")
    movement.set_defaults(handler=handle_sentinel_check_movement)

    botanist = subcommands.add_parser("botanist", help="Botanical intelligence commands.")
    botanist_subcommands = botanist.add_subparsers(dest="botanist_command")
    taxon = botanist_subcommands.add_parser("taxon", help="Resolve a taxon through the fixture GBIF boundary.")
    taxon.add_argument("--query", required=True)
    taxon.set_defaults(handler=handle_botanist_taxon)
    germplasm = botanist_subcommands.add_parser("germplasm", help="Search fixture Genesys germplasm records.")
    germplasm.add_argument("--query", required=True)
    germplasm.add_argument("--limit", type=int, default=10)
    germplasm.set_defaults(handler=handle_botanist_germplasm)

    return parser


def handle_doctor(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        status = cost_status(runtime)
        return {
            "status": "ok",
            "database": args.database,
            "sovereign_mode": args.sovereign,
            "docker_cli_available": shutil.which("docker") is not None,
            "paid_providers_enabled": status["paid_providers_enabled"],
            "automatic_paid_usage_enabled": False,
            "automatic_overage_enabled": False,
            "private_egress_enabled": not args.sovereign,
            "remote_model_egress_enabled": False,
            "available_location_aliases": sorted(runtime.location_aliases),
        }
    finally:
        runtime.close()


def handle_cost_status(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return cost_status(runtime)
    finally:
        runtime.close()


def handle_providers_list(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return {
            "providers": [
                {
                    "provider_id": provider.provider_id,
                    "provider_type": provider.provider_type.value,
                    "billing_class": provider.billing_class.value,
                    "enabled": provider.enabled,
                    "remote": provider.remote,
                    "hard_monthly_usd": provider.cost_policy.hard_monthly_usd,
                    "allow_overage": provider.cost_policy.allow_overage,
                }
                for provider in runtime.registry.all()
            ]
        }
    finally:
        runtime.close()


def handle_eval_run(args: argparse.Namespace) -> JsonDict:
    smoke_file = ROOT / "data" / "evals" / "phase0_smoke_prompts.txt"
    prompts = [line for line in smoke_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"status": "ok" if len(prompts) >= 5 else "failed", "prompt_count": len(prompts), "fixture": str(smoke_file.relative_to(ROOT))}


def handle_sentinel_check_movement(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        origin_id = _location_id(runtime.location_aliases, args.origin)
        destination_id = _location_id(runtime.location_aliases, args.destination)
        decision = asyncio.run(
            runtime.sentinel.check_movement(
                runtime.context(request_id="cli-sentinel"),
                origin_location_id=origin_id,
                destination_location_id=destination_id,
                source_country=args.source_country,
                destination_country=args.destination_country,
                species=args.species,
                plant_part=args.plant_part,
                live_plant=args.live_plant,
                soil_attached=args.soil_attached,
                purpose=args.purpose,
            )
        )
        return asdict(decision)
    finally:
        runtime.close()


def handle_botanist_taxon(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        lookup = asyncio.run(runtime.botanist.resolve_taxon(runtime.context(request_id="cli-botanist"), args.query))
        profile = None
        if lookup.plant_entity is not None:
            profile = asdict(runtime.botanist.build_plant_profile(runtime.organization_id, lookup.plant_entity))
        return {
            "status": lookup.status,
            "plant_entity": asdict(lookup.plant_entity) if lookup.plant_entity else None,
            "plant_profile": profile,
            "warnings": lookup.warnings,
            "source_record_ids": lookup.source_record_ids,
        }
    finally:
        runtime.close()


def handle_botanist_germplasm(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        result = asyncio.run(runtime.botanist.search_germplasm(runtime.context(request_id="cli-germplasm"), args.query, limit=args.limit))
        return result.data
    finally:
        runtime.close()


def _location_id(aliases: dict[str, str], alias: str | None) -> str | None:
    if alias is None:
        return None
    try:
        return aliases[alias]
    except KeyError as exc:
        raise ValueError(f"Unknown location alias: {alias}") from exc


def print_json(payload: JsonDict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
