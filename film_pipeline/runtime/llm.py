from __future__ import annotations

import json
import os
from typing import Any


class LLMClient:
    """Thin OpenAI-compatible client. Dry-run mode skips network."""

    def __init__(self) -> None:
        self.dry_run = os.getenv("FILM_PIPELINE_DRY_RUN", "1").lower() in {
            "1",
            "true",
            "yes",
        }
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        if self.dry_run or not self.api_key:
            raise RuntimeError("LLM dry-run or missing API key — use offline stubs")

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        resp = client.chat.completions.create(
            model=self.model,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
