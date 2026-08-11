from __future__ import annotations

import asyncio
import os
import shutil
import unittest

from packages.vision import OllamaLlavaVisionProvider, VisionRequest


TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def run(coro):
    return asyncio.run(coro)


@unittest.skipUnless(os.environ.get("GAIA_RUN_LLAVA_SMOKE") == "1", "set GAIA_RUN_LLAVA_SMOKE=1 for local LLaVA smoke")
class LlavaVisionSmokeTest(unittest.TestCase):
    def test_local_llava_vision_provider_returns_zero_cost_boundary_response(self) -> None:
        if shutil.which("ollama") is None:
            self.skipTest("ollama executable not found")
        provider = OllamaLlavaVisionProvider(model=os.environ.get("GAIA_LLAVA_MODEL", "llava:latest"), timeout_seconds=120)
        response = run(
            provider.analyze(
                VisionRequest(
                    image_base64=TINY_PNG_BASE64,
                    content_type="image/png",
                    prompt="Describe image quality only. Return cautious JSON.",
                )
            )
        )

        self.assertEqual(response.provider_id, "ollama-llava-local")
        self.assertIn(response.status, {"AVAILABLE", "VALIDATION_FAILED", "PROVIDER_ERROR"})
        self.assertEqual(response.model, os.environ.get("GAIA_LLAVA_MODEL", "llava:latest"))


if __name__ == "__main__":
    unittest.main()

