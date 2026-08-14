from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from apps.api.gaia_api.chat_api import get_conversations, post_chat, stream_chat_message
from apps.api.gaia_api.context_api import post_context_environment, post_context_geography
from apps.api.gaia_api.mercator_api import post_economics_context
from apps.api.gaia_api.plant_api import get_observations, get_plant, get_plants, post_observation, post_plant
from apps.api.gaia_api.research_api import get_research_search, post_research_synthesize
from apps.api.gaia_api.runtime import (
    DEFAULT_ALPHA_HOST,
    DEFAULT_ALPHA_PORT,
    DEFAULT_SQLITE_URL,
    AlphaProviderModes,
    GaiaRuntime,
    architecture_summary,
    cost_status,
    create_runtime,
    locations_payload,
    persistence_summary,
    provider_health_rows,
    provider_mode_for_provider,
    public_geography_for_location,
    runtime_status,
    seed_demo,
    set_active_location,
    source_reconciliation_report,
)
from apps.api.gaia_api.season_api import post_calendar_commit, post_calendar_preview, post_season_plan
from apps.api.gaia_api.sentinel_api import get_active_regulations, get_regulation_zones, post_movement_check
from apps.api.gaia_api.vision_api import post_vision_analyze, post_vision_media


WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class GaiaAlphaHandler(BaseHTTPRequestHandler):
    runtime: GaiaRuntime
    host_name: str
    port_number: int

    server_version = "GAIAAlphaHTTP/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            if path == "/api/v1/status":
                self._json(runtime_status(self.runtime, host=self.host_name, port=self.port_number))
            elif path == "/api/v1/system":
                self._json(system_payload(self.runtime, self.host_name, self.port_number))
            elif path == "/api/v1/dev-identity":
                self._json(dev_identity_payload(self.runtime))
            elif path == "/api/v1/locations":
                self._json(locations_payload(self.runtime))
            elif path == "/api/v1/cost/status":
                self._json(cost_status(self.runtime))
            elif path in {"/api/v1/providers", "/api/v1/providers/list"}:
                self._json(providers_payload(self.runtime))
            elif path == "/api/v1/providers/health":
                self._json(provider_health_payload(self.runtime))
            elif path == "/api/v1/plants":
                self._json(_run(get_plants(self.runtime.repository, self.runtime.context(request_id="api-plants"))))
            elif path.startswith("/api/v1/plants/") and path.endswith("/observations"):
                plant_id = path.split("/")[-2]
                self._json(_run(get_observations(self.runtime.repository, self.runtime.context(request_id="api-observations"), plant_id)))
            elif path.startswith("/api/v1/plants/") and path.endswith("/vision"):
                plant_id = path.split("/")[-2]
                self._json({"visual_analyses": self.runtime.repository.list_visual_analyses_for_plant(self.runtime.organization_id, plant_id)})
            elif path.startswith("/api/v1/plants/"):
                plant_id = path.split("/")[-1]
                payload = _run(get_plant(self.runtime.repository, self.runtime.context(request_id="api-plant"), plant_id))
                self._json(payload if payload is not None else {"status": "not_found"}, status=HTTPStatus.OK if payload else HTTPStatus.NOT_FOUND)
            elif path == "/api/v1/conversations":
                self._json(get_conversations(self.runtime.repository, self.runtime.context(request_id="api-conversations")))
            elif path.startswith("/api/v1/conversations/") and path.endswith("/messages"):
                conversation_id = path.split("/")[-2]
                self._json(self.runtime.repository.list_messages(self.runtime.organization_id, conversation_id))
            elif path == "/api/v1/season/plans":
                self._json({"season_plans": self.runtime.repository.list_season_plans(self.runtime.organization_id, self.runtime.workspace_id)})
            elif path == "/api/v1/regulations/rules":
                self._json(_run(get_active_regulations(self.runtime.repository, self.runtime.context(request_id="api-regulations"))))
            elif path == "/api/v1/regulations/zones":
                self._json(_run(get_regulation_zones(self.runtime.repository, self.runtime.context(request_id="api-zones"))))
            elif path == "/api/v1/source-records":
                ids = ",".join(query.get("ids", [])).split(",") if query.get("ids") else []
                self._json({"source_records": source_records(self.runtime, [item for item in ids if item])})
            elif path == "/api/v1/alpha/persistence-check":
                self._json(persistence_summary(self.runtime))
            elif path.startswith("/api/"):
                self._json({"status": "not_found", "path": path}, status=HTTPStatus.NOT_FOUND)
            else:
                self._static(path)
        except Exception as exc:
            self._json({"status": "error", "error": exc.__class__.__name__, "message": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/api/v1/chat/stream":
                self._chat_stream(self._read_json())
                return
            payload = self._read_json()
            context = self.runtime.context(request_id=str(payload.get("request_id") or f"api-{path.rsplit('/', 1)[-1]}"))
            if path == "/api/v1/seed/demo":
                self._json(seed_demo(self.runtime))
            elif path == "/api/v1/locations/active":
                self._json(_run(set_active_location(self.runtime, **_active_location_payload(payload))))
            elif path == "/api/v1/plants":
                self._json(_run(post_plant(self.runtime.repository, self.runtime.botanist, context, **_plant_payload(payload))))
            elif path.startswith("/api/v1/plants/") and path.endswith("/observations"):
                plant_id = path.split("/")[-2]
                self._json(_run(post_observation(self.runtime.repository, context, plant_id, **_observation_payload(payload))))
            elif path == "/api/v1/chat":
                self._json(_run(post_chat(self.runtime.orchestrator, context, **_chat_payload(self.runtime, payload))))
            elif path == "/api/v1/context/geography":
                self._json(_run(post_context_geography(self.runtime.context_compiler, context, payload.get("location_id") or self.runtime.primary_location_id, payload.get("timestamp"))))
            elif path == "/api/v1/context/environment":
                self._json(_run(post_context_environment(self.runtime.context_compiler, context, payload.get("location_id") or self.runtime.primary_location_id, payload.get("timestamp"))))
            elif path == "/api/v1/vision/media":
                self._json(_run(post_vision_media(self.runtime.vision, context, **_media_payload(payload))))
            elif path == "/api/v1/vision/analyze":
                self._json(_run(post_vision_analyze(self.runtime.vision, context, tool=self.runtime.vision_tool, **_vision_payload(payload))))
            elif path == "/api/v1/research/search":
                self._json(_run(get_research_search(self.runtime.scholar, context, query=str(payload.get("query") or ""), limit=int(payload.get("limit") or 10))))
            elif path == "/api/v1/research/synthesize":
                self._json(_run(post_research_synthesize(self.runtime.scholar, context, question=str(payload.get("question") or ""), user_plant_id=payload.get("user_plant_id"), location_id=payload.get("location_id") or self.runtime.primary_location_id, use_model=bool(payload.get("use_model", False)))))
            elif path == "/api/v1/movement/check":
                self._json(_run(post_movement_check(self.runtime.sentinel, context, **_movement_payload(self.runtime, payload))))
            elif path == "/api/v1/season/plan":
                self._json(_run(post_season_plan(self.runtime.season, self.runtime.season_context_provider, context, **_season_payload(self.runtime, payload))))
            elif path == "/api/v1/calendar/preview":
                self._json(post_calendar_preview(self.runtime.calendar, context, season_plan_id=str(payload["season_plan_id"]), calendar_binding_id=str(payload.get("calendar_binding_id") or self.runtime.calendar_binding_id)))
            elif path == "/api/v1/calendar/commit":
                self._json(_run(post_calendar_commit(self.runtime.calendar, context, preview_id=str(payload["preview_id"]))))
            elif path == "/api/v1/markets/context":
                self._json(_run(post_economics_context(self.runtime.mercator, context, **_market_payload(self.runtime, payload))))
            else:
                self._json({"status": "not_found", "path": path}, status=HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._json({"status": "bad_request", "missing": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._json({"status": "error", "error": exc.__class__.__name__, "message": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[gaia-api] {self.address_string()} - {fmt % args}")

    def _chat_stream(self, payload: dict) -> None:
        context = self.runtime.context(request_id=str(payload.get("request_id") or "api-chat-stream"))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        iterator = stream_chat_message(self.runtime.orchestrator, context, **_chat_payload(self.runtime, payload))
        for event in _run(_collect_events(iterator)):
            chunk = f"event: {event.get('event', 'message')}\ndata: {json.dumps(event, sort_keys=True)}\n\n"
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.flush()
        self.close_connection = True

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _json(self, payload, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, sort_keys=True, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str) -> None:
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        if not str(target).startswith(str(WEB_ROOT.resolve())) or not target.exists() or not target.is_file():
            target = WEB_ROOT / "index.html"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(
    *,
    host: str = DEFAULT_ALPHA_HOST,
    port: int = DEFAULT_ALPHA_PORT,
    database_url: str = DEFAULT_SQLITE_URL,
    sovereign: bool = False,
    provider_modes: AlphaProviderModes | None = None,
) -> None:
    runtime = create_runtime(database_url, sovereign=sovereign, provider_modes=provider_modes)
    handler = type("BoundGaiaAlphaHandler", (GaiaAlphaHandler,), {"runtime": runtime, "host_name": host, "port_number": port})
    httpd = ThreadingHTTPServer((host, port), handler)
    print("GAIA Local Alpha")
    print(f"UI: http://{host}:{port}/")
    print(f"API: http://{host}:{port}/api/v1")
    print(f"Database: {'SQLite' if database_url.startswith('sqlite:///') else database_url}")
    status = runtime_status(runtime, host=host, port=port)
    print(f"Model: {status['text_model']}")
    print(f"Vision: {status['vision_model']}")
    print("Spend policy: $0 automatic paid usage")
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        runtime.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the GAIA local alpha API/UI server.")
    parser.add_argument("--host", default=DEFAULT_ALPHA_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_ALPHA_PORT)
    parser.add_argument("--database", default=DEFAULT_SQLITE_URL)
    parser.add_argument("--sovereign", action="store_true")
    args = parser.parse_args(argv)
    serve(host=args.host, port=args.port, database_url=args.database, sovereign=args.sovereign)
    return 0


async def _collect_events(iterator) -> list[dict]:
    events = []
    async for event in iterator:
        events.append(event)
    return events


def _run(coro):
    return asyncio.run(coro)


def _json_default(value):
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return str(value)


def _plant_payload(payload: dict) -> dict:
    return {
        "taxon_query": str(payload.get("taxon_query") or payload.get("taxon") or "Solanum lycopersicum"),
        "nickname": str(payload.get("nickname") or "New plant"),
        "cultivar": payload.get("cultivar"),
        "planted_at": payload.get("planted_at"),
        "acquired_at": payload.get("acquired_at"),
        "lifecycle_stage": str(payload.get("lifecycle_stage") or "unknown"),
        "location_id": payload.get("location_id"),
        "growing_method": payload.get("growing_method"),
        "tags": payload.get("tags") or [],
    }


def _observation_payload(payload: dict) -> dict:
    return {
        "text": str(payload.get("text") or ""),
        "observed_facts": payload.get("observed_facts") or [],
        "gaia_inferences": payload.get("gaia_inferences") or [],
        "lifecycle_stage_observed": payload.get("lifecycle_stage_observed"),
        "health_tags": payload.get("health_tags") or [],
        "measurements": payload.get("measurements") or {},
        "attachment_references": payload.get("attachment_references") or [],
    }


def _chat_payload(runtime: GaiaRuntime, payload: dict) -> dict:
    return {
        "message": str(payload.get("message") or ""),
        "location_id": payload.get("location_id") or runtime.primary_location_id,
        "user_plant_id": payload.get("user_plant_id"),
        "conversation_id": payload.get("conversation_id"),
    }


def _media_payload(payload: dict) -> dict:
    return {
        "image_base64": str(payload.get("image_base64") or ""),
        "content_type": str(payload.get("content_type") or "image/jpeg"),
        "user_plant_id": payload.get("user_plant_id"),
    }


def _vision_payload(payload: dict) -> dict:
    return {
        "media_attachment_id": str(payload["media_attachment_id"]),
        "user_plant_id": payload.get("user_plant_id"),
        "location_id": payload.get("location_id"),
        "prompt": str(payload.get("prompt") or "Describe visible plant evidence and cautious hypotheses."),
    }


def _movement_payload(runtime: GaiaRuntime, payload: dict) -> dict:
    return {
        "origin_location_id": payload.get("origin_location_id") or runtime.location_aliases.get(str(payload.get("origin_alias") or "")),
        "destination_location_id": payload.get("destination_location_id") or runtime.location_aliases.get(str(payload.get("destination_alias") or "")),
        "species": payload.get("species"),
        "plant_part": str(payload.get("plant_part") or "unknown"),
        "live_plant": bool(payload.get("live_plant", False)),
        "soil_attached": bool(payload.get("soil_attached", False)),
        "planned_date": payload.get("planned_date"),
        "purpose": payload.get("purpose"),
        "source_country": payload.get("source_country"),
        "destination_country": payload.get("destination_country"),
    }


def _season_payload(runtime: GaiaRuntime, payload: dict) -> dict:
    return {
        "workspace_id": runtime.workspace_id,
        "location_id": payload.get("location_id") or runtime.primary_location_id,
        "objective": str(payload.get("objective") or "Create a local alpha season plan."),
        "crop_names": payload.get("crop_names") or ["tomato"],
        "start_date": str(payload.get("start_date") or "2026-09-15"),
        "end_date": str(payload.get("end_date") or "2026-12-15"),
        "constraints": payload.get("constraints") or {},
        "timezone": str(payload.get("timezone") or "America/Chicago"),
        "use_model": bool(payload.get("use_model", False)),
        "include_mercator": bool(payload.get("include_mercator", True)),
    }


def _market_payload(runtime: GaiaRuntime, payload: dict) -> dict:
    location_id = payload.get("location_id") or runtime.primary_location_id
    geography = payload.get("geography") or public_geography_for_location(runtime, location_id)
    return {
        "commodity": str(payload.get("commodity") or "tomato"),
        "geography": geography,
        "location_id": location_id,
        "crop_or_taxon": payload.get("crop_or_taxon") or {},
        "market_region": payload.get("market_region"),
    }


def _active_location_payload(payload: dict) -> dict:
    return {
        "location_id": payload.get("location_id"),
        "label": payload.get("label"),
        "latitude": _float_or_none(payload.get("latitude")),
        "longitude": _float_or_none(payload.get("longitude")),
        "accuracy_m": _float_or_none(payload.get("accuracy_m")),
        "source_kind": str(payload.get("source_kind") or "manual"),
    }


def _float_or_none(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def system_payload(runtime: GaiaRuntime, host: str, port: int) -> dict:
    payload = runtime_status(runtime, host=host, port=port)
    payload["cost"] = cost_status(runtime)
    payload["providers"] = providers_payload(runtime)["providers"]
    payload["persistence"] = persistence_summary(runtime)
    payload["locations"] = locations_payload(runtime)
    payload["architecture"] = architecture_summary(runtime)["orchestration"]
    payload["sources"] = source_reconciliation_report(runtime)["summary"]
    return payload


def dev_identity_payload(runtime: GaiaRuntime) -> dict:
    return {
        "label": "Development Identity",
        "organization_id": runtime.organization_id,
        "user_id": runtime.user_id,
        "workspace_id": runtime.workspace_id,
        "primary_location_id": runtime.primary_location_id,
        "calendar_binding_id": runtime.calendar_binding_id,
        "location_aliases": runtime.location_aliases,
        "active_location": runtime.repository.get_location(runtime.organization_id, runtime.primary_location_id) if runtime.primary_location_id else None,
    }


def providers_payload(runtime: GaiaRuntime) -> dict:
    modes = runtime.provider_modes.to_dict()
    providers = []
    for provider in runtime.registry.all():
        mode = provider_mode_for_provider(provider.provider_id, modes)
        if not provider.enabled:
            mode = "disabled"
        providers.append(
            {
                "provider_id": provider.provider_id,
                "display_name": provider.display_name,
                "provider_type": provider.provider_type.value,
                "billing_class": provider.billing_class.value,
                "enabled": provider.enabled,
                "remote": provider.remote,
                "mode": mode,
                "hard_monthly_usd": provider.cost_policy.hard_monthly_usd,
                "allow_overage": provider.cost_policy.allow_overage,
                "authentication_requirement": provider.authentication_requirement.value,
                "terms_url": provider.license_metadata.terms_url,
                "license": provider.license_metadata.license,
                "attribution_required": provider.license_metadata.attribution_required,
            }
        )
    return {"providers": providers}


def provider_health_payload(runtime: GaiaRuntime) -> dict:
    return {"providers": provider_health_rows(runtime)}


def source_records(runtime: GaiaRuntime, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    rows = runtime.connection.execute(
        f"""
        SELECT * FROM source_records
        WHERE id IN ({placeholders}) AND (organization_id IS NULL OR organization_id = ?) AND deleted_at IS NULL
        ORDER BY provider, title, id
        """,
        (*ids, runtime.organization_id),
    ).fetchall()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    raise SystemExit(main())
