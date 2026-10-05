from __future__ import annotations

import math
import os
from typing import Sequence

import httpx


class EmbeddingProvider:
    async def embed(self, texts: Sequence[str]) -> list[list[float]] | None:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    async def embed(self, texts: Sequence[str]) -> list[list[float]] | None:
        if not self.api_key or not texts:
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": list(texts),
                    "encoding_format": "float",
                },
            )
            if response.is_error:
                return None

            payload = response.json()
            data = sorted(payload.get("data", []), key=lambda item: item["index"])
            return [item["embedding"] for item in data]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
