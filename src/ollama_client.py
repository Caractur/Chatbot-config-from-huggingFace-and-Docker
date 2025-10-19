import httpx
try:
    from .config import OLLAMA_URL, OLLAMA_MODEL, MAX_TOKENS, TEMPERATURE
except ImportError:
    from config import OLLAMA_URL, OLLAMA_MODEL, MAX_TOKENS, TEMPERATURE

SYSTEM = "You are an HTU assistant. Answer using ONLY the provided context. Cite sources with [1], [2]. If insufficient, say you don't know."

def chat(question: str, context: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Q: {question}\n\nContext:\n{context}\n\nA:"}
    ]
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": TEMPERATURE, "num_predict": MAX_TOKENS}
    }
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120.0)
        r.raise_for_status()
        data = r.json()
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        if isinstance(data, dict) and "messages" in data:
            return "\n".join(m.get("content","") for m in data["messages"] if m.get("role") == "assistant")
    except Exception:
        pass

    gen_payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{SYSTEM}\n\nQ: {question}\n\nContext:\n{context}\n\nA:",
        "stream": False,
        "options": {"temperature": TEMPERATURE, "num_predict": MAX_TOKENS}
    }
    r2 = httpx.post(f"{OLLAMA_URL}/api/generate", json=gen_payload, timeout=120.0)
    r2.raise_for_status()
    d2 = r2.json()
    return d2.get("response", "")
