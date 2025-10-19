from typing import List, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

try:
    from .config import (
        EMBEDDING_MODEL, QDRANT_URL, QDRANT_COLLECTION, TOP_K,
        ENABLE_RERANKER, RERANKER_MODEL
    )
    from .ollama_client import chat
except ImportError:
    from config import (
        EMBEDDING_MODEL, QDRANT_URL, QDRANT_COLLECTION, TOP_K,
        ENABLE_RERANKER, RERANKER_MODEL
    )
    from ollama_client import chat

def _device():
    return "cuda" if torch.cuda.is_available() else "cpu"

class Retriever:
    def __init__(self):
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self.client = QdrantClient(QDRANT_URL)

        self.reranker = None
        if ENABLE_RERANKER:
            self.reranker = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL).to(_device())
            self.rtok = AutoTokenizer.from_pretrained(RERANKER_MODEL)

    def embed(self, text: str):
        return self.embedder.encode([text], normalize_embeddings=True)[0].tolist()

    def search(self, question: str, lang: str | None = None, limit: int = TOP_K):
        qvec = self.embed(question)
        pre_limit = max(limit * (3 if self.reranker else 1), limit)
        flt = None
        if lang:
            flt = Filter(must=[FieldCondition(key="lang", match=MatchValue(value=lang))])
        hits = self.client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=qvec,
            query_filter=flt,
            limit=pre_limit,
        )
        docs = [h.payload for h in hits]

        if self.reranker and docs:
            pairs = [(question, d["content"]) for d in docs]
            scores = self._rerank(pairs)
            ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:limit]
            docs = [d for d, s in ranked]
        else:
            docs = docs[:limit]

        context = ""
        for i, d in enumerate(docs, start=1):
            snippet = d["content"][:1200].replace("\n", " ")
            context += f"\n[{i}] {d['url']}\n{snippet}\n"
        return docs, context

    def _rerank(self, pairs: List[tuple[str,str]]):
        toks = self.rtok([p[0] for p in pairs], [p[1] for p in pairs], padding=True, truncation=True, return_tensors="pt").to(_device())
        with torch.no_grad():
            out = self.reranker(**toks).logits.squeeze(-1)
            scores = out.detach().cpu().tolist()
        if isinstance(scores, float): scores = [scores]
        return scores

retriever = Retriever()

def answer(question: str, lang: str | None = None, top_k: int = TOP_K) -> dict:
    docs, ctx = retriever.search(question, lang=lang, limit=top_k)
    text = chat(question, ctx)
    sources = [d["url"] for d in docs]
    return {"answer": text, "sources": sources}
