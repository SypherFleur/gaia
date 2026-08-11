from __future__ import annotations

import asyncio
import os
import shutil
import unittest

from packages.model_gateway import ModelMessage, ModelRequest, OllamaModelProvider


def run(coro):
    return asyncio.run(coro)


@unittest.skipUnless(os.environ.get("GAIA_RUN_OLLAMA_SMOKE") == "1", "set GAIA_RUN_OLLAMA_SMOKE=1 for local Ollama smoke")
class OllamaSmokeTest(unittest.TestCase):
    def test_local_ollama_generates_zero_cost_text(self) -> None:
        if shutil.which("ollama") is None:
            self.skipTest("ollama executable not found")
        provider = OllamaModelProvider(model=os.environ.get("GAIA_OLLAMA_MODEL", "llama3.1:latest"), timeout_seconds=120)
        response = run(
            provider.generate(
                ModelRequest(
                    messages=[
                        ModelMessage(role="system", content="Return a short JSON object."),
                        ModelMessage(role="user", content='Return exactly {"ok":true}.'),
                    ],
                    prompt_id="gaia.smoke",
                    prompt_version="1.0.0",
                    prompt_hash="smoke",
                    response_format="json",
                    max_output_tokens=64,
                    contains_private_text=False,
                )
            )
        )

        self.assertEqual(response.provider_id, "ollama-local")
        self.assertEqual(response.cost_usd, 0.0)
        self.assertTrue(response.content.strip())


if __name__ == "__main__":
    unittest.main()
