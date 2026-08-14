from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from apps.api.gaia_api.runtime import AlphaProviderModes, create_runtime, persistence_summary, seed_demo
from apps.cli.gaia import main


ROOT = Path(__file__).resolve().parents[2]


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


def start_server(port: int, database: str) -> subprocess.Popen:
    env = os.environ.copy()
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


def post_json(url: str, payload: dict) -> dict:
    return json.loads(post_text(url, payload))


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


if __name__ == "__main__":
    unittest.main()
