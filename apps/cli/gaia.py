from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from apps.api.gaia_api.chat_api import post_chat
from apps.api.gaia_api.mercator_api import post_economics_context
from apps.api.gaia_api.plant_api import get_observations, get_plant, get_plants, post_observation, post_plant
from apps.api.gaia_api.research_api import get_research_search, post_research_synthesize
from apps.api.gaia_api.runtime import (
    DEFAULT_ALPHA_HOST,
    DEFAULT_ALPHA_PORT,
    DEFAULT_SQLITE_URL,
    ROOT,
    cost_status,
    create_runtime,
    doctor_report,
    persistence_summary,
    provider_health_rows,
    seed_demo,
)
from apps.api.gaia_api.season_api import post_season_plan
from apps.api.gaia_api.sentinel_api import post_movement_check
from apps.api.gaia_api.vision_api import post_vision_analyze, post_vision_media


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
    exit_code = 0
    if isinstance(result, dict) and result.get("status") == "failed":
        exit_code = 1
    if result is not None:
        print_json(result)
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gaia", description="GAIA local-first command line interface")
    parser.add_argument("--database", default=DEFAULT_SQLITE_URL, help="SQLite URL. Use sqlite:///:memory: for ephemeral fixture runs.")
    parser.add_argument("--sovereign", action="store_true", help="Use sovereign local policy defaults for the command runtime.")
    subcommands = parser.add_subparsers(dest="command")

    doctor = subcommands.add_parser("doctor", help="Check local safety, provider, Docker, and zero-spend posture.")
    doctor.add_argument("--host", default=DEFAULT_ALPHA_HOST)
    doctor.add_argument("--port", type=int, default=DEFAULT_ALPHA_PORT)
    doctor.set_defaults(handler=handle_doctor)

    dev = subcommands.add_parser("dev", help="Start the GAIA local alpha API and browser UI.")
    dev.add_argument("--host", default=DEFAULT_ALPHA_HOST)
    dev.add_argument("--port", type=int, default=DEFAULT_ALPHA_PORT)
    dev.add_argument("--startup-timeout", type=float, default=20.0)
    dev.add_argument("--smoke-seconds", type=float, default=None, help="Test helper: stop cleanly after the server becomes reachable.")
    dev.set_defaults(handler=handle_dev)

    seed = subcommands.add_parser("seed", help="Seed local alpha data.")
    seed_subcommands = seed.add_subparsers(dest="seed_command")
    seed_demo_cmd = seed_subcommands.add_parser("demo", help="Seed the Cherokee Purple Tomato manual alpha workspace.")
    seed_demo_cmd.set_defaults(handler=handle_seed_demo)

    cost = subcommands.add_parser("cost", help="Cost and spend controls.")
    cost_subcommands = cost.add_subparsers(dest="cost_command")
    cost_status_cmd = cost_subcommands.add_parser("status", help="Show cost status.")
    cost_status_cmd.set_defaults(handler=handle_cost_status)

    providers = subcommands.add_parser("providers", help="Provider registry inspection.")
    providers_subcommands = providers.add_subparsers(dest="providers_command")
    providers_list = providers_subcommands.add_parser("list", help="List configured providers.")
    providers_list.set_defaults(handler=handle_providers_list)
    providers_health = providers_subcommands.add_parser("health", help="Show provider health states.")
    providers_health.set_defaults(handler=handle_providers_health)

    chat = subcommands.add_parser("chat", help="Ask GAIA through the local orchestrator.")
    chat.add_argument("message")
    chat.add_argument("--plant-id")
    chat.add_argument("--location", default="tx-austin")
    chat.set_defaults(handler=handle_chat)

    plant = subcommands.add_parser("plant", help="Plant workspace commands.")
    plant_subcommands = plant.add_subparsers(dest="plant_command")
    plant_list = plant_subcommands.add_parser("list", help="List plants.")
    plant_list.set_defaults(handler=handle_plant_list)
    plant_add = plant_subcommands.add_parser("add", help="Create a plant.")
    plant_add.add_argument("--taxon", required=True)
    plant_add.add_argument("--nickname", required=True)
    plant_add.add_argument("--cultivar")
    plant_add.add_argument("--location", default="tx-austin")
    plant_add.set_defaults(handler=handle_plant_add)
    plant_show = plant_subcommands.add_parser("show", help="Show a plant.")
    plant_show.add_argument("plant_id")
    plant_show.set_defaults(handler=handle_plant_show)
    plant_observe = plant_subcommands.add_parser("observe", help="Add an observation.")
    plant_observe.add_argument("plant_id")
    plant_observe.add_argument("--text", required=True)
    plant_observe.set_defaults(handler=handle_plant_observe)

    vision = subcommands.add_parser("vision", help="Vision commands.")
    vision_subcommands = vision.add_subparsers(dest="vision_command")
    vision_analyze = vision_subcommands.add_parser("analyze", help="Analyze an image.")
    vision_analyze.add_argument("image")
    vision_analyze.add_argument("--plant-id")
    vision_analyze.add_argument("--content-type", default="image/jpeg")
    vision_analyze.set_defaults(handler=handle_vision_analyze)

    botanist = subcommands.add_parser("botanist", help="Botanical intelligence commands.")
    botanist_subcommands = botanist.add_subparsers(dest="botanist_command")
    taxon = botanist_subcommands.add_parser("taxon", help="Resolve a taxon through the GBIF boundary.")
    taxon.add_argument("--query", required=True)
    taxon.set_defaults(handler=handle_botanist_taxon)
    germplasm = botanist_subcommands.add_parser("germplasm", help="Search Genesys germplasm records.")
    germplasm.add_argument("--query", required=True)
    germplasm.add_argument("--limit", type=int, default=10)
    germplasm.set_defaults(handler=handle_botanist_germplasm)

    scholar = subcommands.add_parser("scholar", help="Research evidence commands.")
    scholar_subcommands = scholar.add_subparsers(dest="scholar_command")
    scholar_search = scholar_subcommands.add_parser("search", help="Search research.")
    scholar_search.add_argument("--query", required=True)
    scholar_search.add_argument("--limit", type=int, default=5)
    scholar_search.set_defaults(handler=handle_scholar_search)
    scholar_synthesize = scholar_subcommands.add_parser("synthesize", help="Synthesize evidence.")
    scholar_synthesize.add_argument("--question", required=True)
    scholar_synthesize.set_defaults(handler=handle_scholar_synthesize)

    sentinel = subcommands.add_parser("sentinel", help="Sentinel regulatory checks.")
    sentinel_subcommands = sentinel.add_subparsers(dest="sentinel_command")
    movement = sentinel_subcommands.add_parser("check-movement", help="Run a movement check.")
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

    season = subcommands.add_parser("season", help="Season planning commands.")
    season_subcommands = season.add_subparsers(dest="season_command")
    season_plan = season_subcommands.add_parser("plan", help="Create a Season Plan.")
    season_plan.add_argument("--crops", default="tomato")
    season_plan.add_argument("--goal", default="Create a local alpha season plan.")
    season_plan.add_argument("--start-date", default="2026-09-15")
    season_plan.add_argument("--end-date", default="2026-12-15")
    season_plan.add_argument("--location", default="tx-austin")
    season_plan.set_defaults(handler=handle_season_plan)
    season_show = season_subcommands.add_parser("show", help="List Season Plans.")
    season_show.set_defaults(handler=handle_season_show)

    mercator = subcommands.add_parser("mercator", help="Market and regional context commands.")
    mercator_subcommands = mercator.add_subparsers(dest="mercator_command")
    mercator_context = mercator_subcommands.add_parser("context", help="Build Mercator context.")
    mercator_context.add_argument("--commodity", default="tomato")
    mercator_context.set_defaults(handler=handle_mercator_context)

    research = subcommands.add_parser("research", help="Institutional research commands.")
    research_subcommands = research.add_subparsers(dest="research_command")
    research_run = research_subcommands.add_parser("run", help="Run a fixture-backed evidence synthesis.")
    research_run.add_argument("--question", default="What evidence should guide Cherokee Purple Tomato care?")
    research_run.set_defaults(handler=handle_research_run)
    research_export = research_subcommands.add_parser("export", help="Export local research summary.")
    research_export.set_defaults(handler=handle_research_export)

    eval_cmd = subcommands.add_parser("eval", help="Evaluation harness commands.")
    eval_subcommands = eval_cmd.add_subparsers(dest="eval_command")
    eval_run = eval_subcommands.add_parser("run", help="Run the smoke eval fixture check.")
    eval_run.set_defaults(handler=handle_eval_run)

    return parser


def handle_doctor(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return doctor_report(runtime, host=args.host, port=args.port)
    finally:
        runtime.close()


def handle_dev(args: argparse.Namespace) -> JsonDict:
    command = [
        sys.executable,
        "-m",
        "apps.api.gaia_api.server",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--database",
        args.database,
    ]
    if args.sovereign:
        command.append("--sovereign")
    process = subprocess.Popen(command, cwd=ROOT)
    url = f"http://{args.host}:{args.port}/api/v1/status"
    try:
        readiness = _wait_for_gaia_server(url, process, args.startup_timeout)
        if not readiness["ready"]:
            _terminate(process)
            return {
                "status": "failed",
                "reason": readiness["reason"],
                "detail": readiness.get("detail"),
                "exit_code": readiness.get("exit_code"),
                "command": _copy_paste_command(args),
                "ui_url": f"http://{args.host}:{args.port}/",
            }
        print("GAIA Local Alpha")
        print(f"UI: http://{args.host}:{args.port}/")
        print(f"API: http://{args.host}:{args.port}/api/v1")
        print("Database: SQLite")
        print(f"Model: {_text_model_label()}")
        print(f"Vision: {_vision_model_label()}")
        print("Spend policy: $0 automatic paid usage")
        if args.smoke_seconds is not None:
            time.sleep(args.smoke_seconds)
            _terminate(process)
            return {"status": "ok", "mode": "smoke", "command": _copy_paste_command(args), "ui_url": f"http://{args.host}:{args.port}/"}
        while process.poll() is None:
            time.sleep(0.5)
        return {"status": "stopped", "exit_code": process.returncode, "ui_url": f"http://{args.host}:{args.port}/"}
    except KeyboardInterrupt:
        _terminate(process)
        return {"status": "stopped", "reason": "keyboard_interrupt", "ui_url": f"http://{args.host}:{args.port}/"}


def handle_seed_demo(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return seed_demo(runtime)
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


def handle_providers_health(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return {"providers": provider_health_rows(runtime)}
    finally:
        runtime.close()


def handle_chat(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(
            post_chat(
                runtime.orchestrator,
                runtime.context(request_id="cli-chat"),
                message=args.message,
                location_id=_location_id(runtime.location_aliases, args.location) or runtime.primary_location_id,
                user_plant_id=args.plant_id,
            )
        )
    finally:
        runtime.close()


def handle_plant_list(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return {"plants": _run(get_plants(runtime.repository, runtime.context(request_id="cli-plant-list")))}
    finally:
        runtime.close()


def handle_plant_add(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(
            post_plant(
                runtime.repository,
                runtime.botanist,
                runtime.context(request_id="cli-plant-add"),
                taxon_query=args.taxon,
                nickname=args.nickname,
                cultivar=args.cultivar,
                location_id=_location_id(runtime.location_aliases, args.location),
            )
        )
    finally:
        runtime.close()


def handle_plant_show(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        payload = _run(get_plant(runtime.repository, runtime.context(request_id="cli-plant-show"), args.plant_id))
        return payload or {"status": "not_found"}
    finally:
        runtime.close()


def handle_plant_observe(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(post_observation(runtime.repository, runtime.context(request_id="cli-plant-observe"), args.plant_id, text=args.text))
    finally:
        runtime.close()


def handle_vision_analyze(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        image_base64 = base64.b64encode(Path(args.image).read_bytes()).decode("ascii")
        media = _run(post_vision_media(runtime.vision, runtime.context(request_id="cli-vision-media"), image_base64=image_base64, content_type=args.content_type, user_plant_id=args.plant_id))
        return _run(
            post_vision_analyze(
                runtime.vision,
                runtime.context(request_id="cli-vision-analyze"),
                tool=runtime.vision_tool,
                media_attachment_id=media["id"],
                user_plant_id=args.plant_id,
                location_id=runtime.primary_location_id,
            )
        )
    finally:
        runtime.close()


def handle_botanist_taxon(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        lookup = _run(runtime.botanist.resolve_taxon(runtime.context(request_id="cli-botanist"), args.query))
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
        result = _run(runtime.botanist.search_germplasm(runtime.context(request_id="cli-germplasm"), args.query, limit=args.limit))
        return result.data
    finally:
        runtime.close()


def handle_scholar_search(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(get_research_search(runtime.scholar, runtime.context(request_id="cli-scholar-search"), query=args.query, limit=args.limit))
    finally:
        runtime.close()


def handle_scholar_synthesize(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(post_research_synthesize(runtime.scholar, runtime.context(request_id="cli-scholar-synthesize"), question=args.question, use_model=False))
    finally:
        runtime.close()


def handle_sentinel_check_movement(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(
            post_movement_check(
                runtime.sentinel,
                runtime.context(request_id="cli-sentinel"),
                origin_location_id=_location_id(runtime.location_aliases, args.origin),
                destination_location_id=_location_id(runtime.location_aliases, args.destination),
                source_country=args.source_country,
                destination_country=args.destination_country,
                species=args.species,
                plant_part=args.plant_part,
                live_plant=args.live_plant,
                soil_attached=args.soil_attached,
                purpose=args.purpose,
            )
        )
    finally:
        runtime.close()


def handle_season_plan(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(
            post_season_plan(
                runtime.season,
                runtime.season_context_provider,
                runtime.context(request_id="cli-season-plan"),
                workspace_id=runtime.workspace_id,
                location_id=_location_id(runtime.location_aliases, args.location),
                objective=args.goal,
                crop_names=[crop.strip() for crop in args.crops.split(",") if crop.strip()],
                start_date=args.start_date,
                end_date=args.end_date,
                timezone="America/Chicago",
                include_mercator=True,
            )
        )
    finally:
        runtime.close()


def handle_season_show(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return {"season_plans": runtime.repository.list_season_plans(runtime.organization_id, runtime.workspace_id)}
    finally:
        runtime.close()


def handle_mercator_context(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return _run(
            post_economics_context(
                runtime.mercator,
                runtime.context(request_id="cli-mercator"),
                commodity=args.commodity,
                geography={"country_code": "US", "state_code": "TX", "county_or_district": "Travis County", "county_fips": "48453"},
                location_id=runtime.primary_location_id,
            )
        )
    finally:
        runtime.close()


def handle_research_run(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        synthesis = _run(post_research_synthesize(runtime.scholar, runtime.context(request_id="cli-research-run"), question=args.question, use_model=False))
        return {"status": "ok", "synthesis": synthesis, "persistence": persistence_summary(runtime)}
    finally:
        runtime.close()


def handle_research_export(args: argparse.Namespace) -> JsonDict:
    runtime = create_runtime(args.database, sovereign=args.sovereign)
    try:
        return {"status": "ok", "export": persistence_summary(runtime), "contains_secrets": False}
    finally:
        runtime.close()


def handle_eval_run(args: argparse.Namespace) -> JsonDict:
    smoke_file = ROOT / "data" / "evals" / "phase0_smoke_prompts.txt"
    prompts = [line for line in smoke_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"status": "ok" if len(prompts) >= 5 else "failed", "prompt_count": len(prompts), "fixture": str(smoke_file.relative_to(ROOT))}


def _location_id(aliases: dict[str, str], alias: str | None) -> str | None:
    if alias is None:
        return None
    try:
        return aliases[alias]
    except KeyError as exc:
        raise ValueError(f"Unknown location alias: {alias}") from exc


def _run(coro):
    return asyncio.run(coro)


def _wait_for_gaia_server(url: str, process: subprocess.Popen, timeout_seconds: float) -> JsonDict:
    deadline = time.time() + timeout_seconds
    last_error = "not reachable yet"
    while time.time() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            return {"ready": False, "reason": "server_process_exited", "exit_code": exit_code, "detail": last_error}
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if (
                    response.status == 200
                    and payload.get("name") == "GAIA Local Alpha"
                    and payload.get("spend_policy") == "$0 automatic paid usage"
                ):
                    return {"ready": True, "reason": "ok"}
                last_error = "unexpected response at GAIA status URL"
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last_error = exc.__class__.__name__
            time.sleep(0.2)
    return {"ready": False, "reason": "server_not_reachable", "detail": last_error}


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=8)


def _copy_paste_command(args: argparse.Namespace) -> str:
    return f"py -3.13 -m apps.cli.gaia --database {args.database} dev --host {args.host} --port {args.port}"


def _text_model_label() -> str:
    import os

    return os.environ.get("GAIA_OLLAMA_MODEL", "llama3.1:latest") if os.environ.get("GAIA_TEXT_MODEL_MODE", "local").lower() == "local" else "fixture-guidance-local"


def _vision_model_label() -> str:
    import os

    return os.environ.get("GAIA_LLAVA_MODEL", "llava:latest") if os.environ.get("GAIA_VISION_MODEL_MODE", "local").lower() == "local" else "fixture-vision-local"


def print_json(payload: JsonDict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
