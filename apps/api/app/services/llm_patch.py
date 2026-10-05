from __future__ import annotations

import json
import os
from typing import Any

import httpx


class PatchModel:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = os.getenv("PATCH_MODEL", "gpt-6-luna")

    async def propose(
        self,
        task: str,
        hypothesis: str,
        files: list[dict[str, str]],
    ) -> list[dict[str, str]] | None:
        if not self.api_key or not files:
            return None

        prompt = {
            "task": task,
            "hypothesis": hypothesis,
            "files": files,
            "instructions": [
                "Return JSON only.",
                "Propose the smallest defensible code change.",
                "Do not invent files or APIs not present in the supplied source.",
                "Each unified_diff must be a valid unified diff for exactly one supplied file.",
                "Do not include markdown fences.",
            ],
            "output_schema": {
                "patches": [
                    {
                        "path": "existing/file/path",
                        "rationale": "why this change addresses the task",
                        "unified_diff": "--- a/path\n+++ b/path\n@@ ...",
                    }
                ]
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are ForgeAI's patch planner. Produce conservative, "
                                "evidence-grounded code patches as strict JSON."
                            ),
                        },
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            if response.is_error:
                return None

        try:
            content = response.json()["choices"][0]["message"]["content"]
            payload: dict[str, Any] = json.loads(content)
            patches = payload.get("patches")
            if not isinstance(patches, list):
                return None
            return [
                item for item in patches
                if isinstance(item, dict)
                and isinstance(item.get("path"), str)
                and isinstance(item.get("rationale"), str)
                and isinstance(item.get("unified_diff"), str)
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
