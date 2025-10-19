from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

try:
    from src.rag_service_local import answer
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from rag_service_local import answer

app = FastAPI(title="HTU RAG API (Local)")

class AskReq(BaseModel):
    question: str
    top_k: int = 6
    lang: Optional[str] = None  # "en" or "ar"

@app.post("/ask")
def ask(req: AskReq):
    res = answer(req.question, lang=req.lang, top_k=req.top_k)
    return res
