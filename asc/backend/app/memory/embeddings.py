"""Deterministic, dependency-free text embeddings.

A production system would call a real embedding model (e.g. DashScope's
text-embedding endpoint). To keep the platform self-contained and testable
offline, this uses a hashed bag-of-words projection into a fixed-dimension
vector. It is deterministic and gives meaningful cosine similarity for keyword
overlap, which is enough for semantic-ish recall in dev and tests.
"""

import hashlib
import math
import re
from typing import List

from app.core.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def embed(text: str, dim: int | None = None) -> List[float]:
    """Return an L2-normalized embedding vector for ``text``."""
    dim = dim or settings.EMBEDDING_DIM
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
