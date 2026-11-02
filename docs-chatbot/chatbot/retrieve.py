"""Retrieval: find the passages most relevant to a question.

Uses TF-IDF with word and character n-grams, which needs no external service and copes with plurals and typos
("e-bike", "ebike", "refunds"). For large knowledge bases, swap in an embedding model; the interface stays the same.
"""
from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from .ingest import Chunk

SYNONYMS = {  # small domain thesaurus: customer words -> document words
    "money back": "refund", "send back": "return", "guarantee": "warranty", "repair": "service workshop",
    "open": "opening hours", "shipping": "delivery", "postage": "delivery", "ebike": "e-bike", "electric bike": "e-bike",
    "cost": "price £", "how much": "price £", "phone number": "phone contact", "where are you": "store locations", "where is": "store locations address", "shop": "store",
    "keep my bike": "hold bikes storage", "pick up": "collect collection", "discount": "% off members",
}


def expand(q: str) -> str:
    ql = q.lower()
    return q + " " + " ".join(v for k, v in SYNONYMS.items() if k in ql)


class Index:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.vec = FeatureUnion([
            ("words", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")),
            ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
        ])
        docs = [f"{c.location} {c.text}" for c in chunks]
        self.m = self.vec.fit_transform(docs)
        self.m = self.m.multiply(1 / (np.sqrt(self.m.multiply(self.m).sum(axis=1)) + 1e-9)).tocsr()

    def search(self, question: str, k: int = 4):
        v = self.vec.transform([expand(question)])
        v = v.multiply(1 / (np.sqrt(v.multiply(v).sum()) + 1e-9))
        scores = np.asarray((self.m @ v.T).todense()).ravel()
        order = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9£]+", s.lower()))
