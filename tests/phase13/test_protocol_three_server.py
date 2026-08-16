from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from apps.api.gaia_api.runtime import AlphaProviderModes, create_runtime, persistence_summary, seed_demo
from apps.cli.gaia import main


ROOT = Path(__file__).resolve().parents[2]
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


class ProtocolThreeServerTest(unittest.TestCase):
    def test_seed_demo_persists_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = f"sqlite:///{Path(tmp) / 'gaia-alpha.sqlite3'}"
            runtime = create_runtime(database, provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
            try:
                first = seed_demo(runtime)
                self.assertEqual(first["plant_count"], 1)
                self.assertEqual(first["guidance_plan_count"], 1)
            finally:
                runtime.close()

            restarted = create_runtime(database, provider_modes=AlphaProviderModes(text_model="fixture", vision_model="fixture"))
            try:
                demo_workspace = restarted.connection.execute(
                    "SELECT id FROM workspaces WHERE organization_id = ? AND name = 'Demo Workspace' AND deleted_at IS NULL",
                    (restarted.organization_id,),
                ).fetchone()
                self.assertIsNotNone(demo_workspace)
                restarted.workspace_id = demo_workspace["id"]
                summary = persistence_summary(restarted)
                self.assertGreaterEqual(summary["plant_count"], 1)
                self.assertGreaterEqual(summary["observation_count"], 1)
                self.assertGreaterEqual(summary["guidance_plan_count"], 1)
            finally:
                restarted.close()

    def test_local_server_route_contracts_and_chat_sse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-server.sqlite3'}"
            process = start_server(port, database)
            try:
                status = wait_json(f"http://127.0.0.1:{port}/api/v1/status")
                self.assertEqual(status["status"], "ok")
                self.assertEqual(status["spend_policy"], "$0 automatic paid usage")

                seed = post_json(f"http://127.0.0.1:{port}/api/v1/seed/demo", {})
                self.assertEqual(seed["status"], "ok")
                plants = wait_json(f"http://127.0.0.1:{port}/api/v1/plants")
                self.assertEqual(len(plants), 1)

                geography = post_json(
                    f"http://127.0.0.1:{port}/api/v1/context/geography",
                    {"location_id": seed["primary_location_id"]},
                )
                self.assertEqual(geography["geo_context"]["county_or_district"], "Travis County")

                stream = post_text(
                    f"http://127.0.0.1:{port}/api/v1/chat/stream",
                    {"message": "What county am I in?", "location_id": seed["primary_location_id"]},
                )
                self.assertIn("event: route", stream)
                self.assertIn('"route": "geography"', stream)
                self.assertIn("event: final", stream)
            finally:
                stop_server(process)

    def test_plant_patch_and_delete_routes_are_reachable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-plant-edit.sqlite3'}"
            process = start_server(port, database)
            try:
                base = f"http://127.0.0.1:{port}"
                wait_json(f"{base}/api/v1/status")
                post_json(f"{base}/api/v1/seed/demo", {})
                plant_id = wait_json(f"{base}/api/v1/plants")[0]["id"]

                patched = request_json(f"{base}/api/v1/plants/{plant_id}", {"nickname": "Renamed tomato", "tags": ["patio"]}, method="PATCH")
                self.assertEqual(patched["status"], "updated")
                self.assertEqual(patched["plant"]["nickname"], "Renamed tomato")
                self.assertEqual(patched["plant"]["tags"], ["patio"])

                deleted = request_json(f"{base}/api/v1/plants/{plant_id}", None, method="DELETE")
                self.assertEqual(deleted["status"], "deleted")
                self.assertEqual(wait_json(f"{base}/api/v1/plants"), [])

                missing = request_json(f"{base}/api/v1/plants/does-not-exist", None, method="DELETE")
                self.assertEqual(missing["status"], "not_found")
            finally:
                stop_server(process)

    def test_server_errors_do_not_leak_exception_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-error.sqlite3'}"
            process = start_server(port, database)
            try:
                base = f"http://127.0.0.1:{port}"
                wait_json(f"{base}/api/v1/status")
                # calendar/preview requires season_plan_id; a bogus one raises internally.
                failure = request_json(f"{base}/api/v1/calendar/preview", {"season_plan_id": "does-not-exist"}, method="POST")

                self.assertEqual(failure["error"], "internal_error")
                self.assertTrue(failure["error_reference"])
                self.assertNotIn("message", failure)
                self.assertNotIn("Traceback", json.dumps(failure))
                self.assertNotIn(str(Path(tmp)), json.dumps(failure))
            finally:
                stop_server(process)

    def test_static_alpha_workspace_is_served(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-static.sqlite3'}"
            process = start_server(port, database)
            try:
                wait_json(f"http://127.0.0.1:{port}/api/v1/status")
                html = get_text(f"http://127.0.0.1:{port}/")
                javascript = get_text(f"http://127.0.0.1:{port}/app.js")
                stylesheet = get_text(f"http://127.0.0.1:{port}/styles.css")

                # Shell: ontology explorer, three pillars, inspector.
                self.assertIn("GAIA Workbench", html)
                self.assertIn('data-pillar="planning"', html)
                self.assertIn('data-pillar="evidence"', html)
                self.assertIn('data-pillar="identify"', html)
                self.assertIn('id="object-types"', html)
                self.assertIn('id="inspector"', html)
                self.assertIn("Use device", html)

                # The console must keep surfacing cost posture, provenance, and
                # the fact that deterministic routes cost no model run.
                self.assertIn("/api/v1/seed/demo", javascript)
                self.assertIn("source_kind: \"device\"", javascript)
                self.assertIn("automatic_paid_usage_enabled", javascript)
                self.assertIn("source_record_ids", javascript)
                self.assertIn("model_run_count", javascript)
                self.assertIn("/api/v1/source-records", javascript)
                self.assertIn(".shell", stylesheet)
                self.assertIn(".inspector", stylesheet)
                self.assertIn(".provenance", stylesheet)

                # Absent data must never render as a blank or a default.
                self.assertIn("unavailable", javascript)
                self.assertNotIn("static demo", javascript.lower())
            finally:
                stop_server(process)

    def test_manual_alpha_fixture_scenarios_cover_owner_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-owner-smoke.sqlite3'}"
            process = start_server(port, database)
            try:
                base = f"http://127.0.0.1:{port}"
                wait_json(f"{base}/api/v1/status")
                seed = post_json(f"{base}/api/v1/seed/demo", {})
                plants = wait_json(f"{base}/api/v1/plants")
                plant_id = plants[0]["id"]

                geography = post_json(f"{base}/api/v1/context/geography", {"location_id": seed["primary_location_id"]})
                self.assertEqual(geography["geo_context"]["county_or_district"], "Travis County")

                environment = post_json(f"{base}/api/v1/context/environment", {"location_id": seed["primary_location_id"]})
                self.assertEqual(environment["model_run_count"], 0)
                self.assertIn(environment["environmental_snapshot"]["provider_statuses"]["nws"], {"AVAILABLE", "CACHE_HIT"})

                research = post_json(
                    f"{base}/api/v1/research/synthesize",
                    {"question": "What research supports tomato companion planting?", "user_plant_id": plant_id, "use_model": False},
                )
                self.assertIn("evidence_quality", research)

                movement = post_json(
                    f"{base}/api/v1/movement/check",
                    {
                        "origin_alias": "tx-houston",
                        "destination_alias": "fl-orlando",
                        "species": "Citrus sinensis",
                        "plant_part": "live plant",
                        "live_plant": True,
                    },
                )
                self.assertEqual(movement["status"], "RESTRICTED")
                self.assertTrue(any(rule["jurisdiction_pack"] == "us_fl" for rule in movement["applicable_rules"]))

                market = post_json(f"{base}/api/v1/markets/context", {"commodity": "tomato", "location_id": seed["primary_location_id"]})
                self.assertEqual(market["commodity"]["canonical_name"], "tomato")
                self.assertIn("markets", market["freshness"])

                chat = post_json(
                    f"{base}/api/v1/chat",
                    {"message": "What is the tomato market context?", "location_id": seed["primary_location_id"], "user_plant_id": plant_id},
                )
                self.assertEqual(chat["route"], "economics")
                self.assertTrue(chat["source_record_ids"])

                media = post_json(
                    f"{base}/api/v1/vision/media",
                    {"image_base64": TINY_PNG_BASE64, "content_type": "image/png", "user_plant_id": plant_id},
                )
                analysis = post_json(
                    f"{base}/api/v1/vision/analyze",
                    {"media_attachment_id": media["id"], "user_plant_id": plant_id, "location_id": seed["primary_location_id"]},
                )
                self.assertIn(analysis["provider_status"], {"AVAILABLE", "VALIDATION_FAILED"})
                self.assertNotIn("inline_base64", media["metadata"])

                season = post_json(
                    f"{base}/api/v1/season/plan",
                    {
                        "crop_names": ["tomato"],
                        "objective": "Create a fall care plan for Cherokee Purple Tomato.",
                        "start_date": "2026-09-15",
                        "end_date": "2026-12-15",
                        "location_id": seed["primary_location_id"],
                        "include_mercator": True,
                    },
                )
                self.assertTrue(season["actions"])
                calendar = post_json(f"{base}/api/v1/calendar/preview", {"season_plan_id": season["season_plan"]["id"]})
                self.assertEqual(calendar["status"], "preview")
                self.assertTrue(calendar["event_previews"])

                system = wait_json(f"{base}/api/v1/system")
                self.assertEqual(system["cost"]["total_development_cash_spent"], 0.0)
                self.assertFalse(system["cost"]["paid_providers_enabled"])
                self.assertGreaterEqual(system["persistence"]["guidance_plan_count"], 1)
            finally:
                stop_server(process)

    def test_gaia_dev_smoke_starts_and_shuts_down_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-dev.sqlite3'}"
            old_text_mode = os.environ.get("GAIA_TEXT_MODEL_MODE")
            old_vision_mode = os.environ.get("GAIA_VISION_MODEL_MODE")
            os.environ["GAIA_TEXT_MODEL_MODE"] = "fixture"
            os.environ["GAIA_VISION_MODEL_MODE"] = "fixture"
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["--database", database, "dev", "--port", str(port), "--startup-timeout", "12", "--smoke-seconds", "0.1"])
                self.assertEqual(code, 0, output.getvalue())
                self.assertIn("GAIA Local Alpha", output.getvalue())
                self.assertIn(f"http://127.0.0.1:{port}/", output.getvalue())
                time.sleep(0.5)
                self.assertFalse(is_reachable(f"http://127.0.0.1:{port}/api/v1/status"))
            finally:
                restore_env("GAIA_TEXT_MODEL_MODE", old_text_mode)
                restore_env("GAIA_VISION_MODEL_MODE", old_vision_mode)

    def test_gaia_dev_fails_on_port_collision_with_non_gaia_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            database = f"sqlite:///{Path(tmp) / 'gaia-port-collision.sqlite3'}"
            fake_server = ThreadingHTTPServer(("127.0.0.1", port), FakeStatusHandler)
            thread = threading.Thread(target=fake_server.serve_forever, daemon=True)
            thread.start()
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(["--database", database, "dev", "--port", str(port), "--startup-timeout", "4", "--smoke-seconds", "0.1"])
                payload = json.loads(output.getvalue())

                self.assertEqual(code, 1)
                self.assertEqual(payload["status"], "failed")
                self.assertIn(payload["reason"], {"server_process_exited", "server_not_reachable"})
            finally:
                fake_server.shutdown()
                fake_server.server_close()
                thread.join(timeout=5)


def start_server(port: int, database: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["GAIA_RUNTIME_MODE"] = "demo"
    env["GAIA_TEXT_MODEL_MODE"] = "fixture"
    env["GAIA_VISION_MODEL_MODE"] = "fixture"
    process = subprocess.Popen(
        [sys.executable, "-m", "apps.api.gaia_api.server", "--port", str(port), "--database", database],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    return process


def stop_server(process: subprocess.Popen) -> None:
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=8)
    finally:
        if process.stdout is not None:
            process.stdout.close()


def wait_json(url: str, timeout: float = 12.0) -> dict:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(0.2)
    raise AssertionError(f"{url} did not become reachable: {last_error}")


def get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def post_json(url: str, payload: dict) -> dict:
    return json.loads(post_text(url, payload))


def request_json(url: str, payload: dict | None, *, method: str) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


def post_text(url: str, payload: dict) -> str:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def is_reachable(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return response.status == 200
    except urllib.error.URLError:
        return False


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def restore_env(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


class FakeStatusHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/v1/status":
            body = json.dumps({"name": "not GAIA", "status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        return


if __name__ == "__main__":
    unittest.main()
