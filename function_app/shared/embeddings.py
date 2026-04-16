"""Embeddings — text-embedding-3-small, batched, with retry.

Kept identical to ingest_prod.py:embed_batch for parity with the 543 chunks
already in the prod index.
"""

from __future__ import annotations

import time

from . import aoai_client, config


def embed_batch(texts: list[str]) -> list[list[float]]:
    client = aoai_client.get_aoai_client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), config.EMBED_BATCH_SIZE):
        sub = texts[i : i + config.EMBED_BATCH_SIZE]
        for attempt in range(3):
            try:
                resp = client.embeddings.create(model=config.EMBED_DEPLOYMENT, input=sub)
                vectors.extend([d.embedding for d in resp.data])
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(10 * (attempt + 1))
    return vectors
