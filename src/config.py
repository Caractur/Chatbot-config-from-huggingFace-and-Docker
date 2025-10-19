import os
from dotenv import load_dotenv
load_dotenv()

# Crawl
ALLOWED_DOMAINS = set(d.strip() for d in os.getenv("ALLOWED_DOMAINS", "htu.edu.jo").split(",") if d.strip())
START_URLS = [s.strip() for s in os.getenv("START_URLS", "https://www.htu.edu.jo/,https://www.htu.edu.jo/ar/").split(",") if s.strip()]
CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "2000"))
CRAWL_RATE_SECONDS = float(os.getenv("CRAWL_RATE_SECONDS", "0.6"))
USER_AGENT_NAME = os.getenv("USER_AGENT_NAME", "HTUAssistantBot/1.0")
USER_AGENT_EMAIL = os.getenv("USER_AGENT_EMAIL", "you@example.com")
USER_AGENT = f"{USER_AGENT_NAME} (contact: {USER_AGENT_EMAIL})"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
OUTPUT_JSONL = os.path.join(DATA_DIR, "university_corpus.jsonl")

# Embeddings & DB
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "htu-web")
QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "Cosine")

# LLM via Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "700"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))

# Reranker
ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "true").lower() == "true"
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
TOP_K = int(os.getenv("TOP_K", "6"))
