# Chatbot-config-from-huggingFace-and-Docker

A local Retrieval-Augmented Generation (RAG) system for HTU website content with multilingual support (English/Arabic), using Ollama LLM, Qdrant vector DB, and FastAPI. Includes web crawler, embedding models, and reranking for accurate Q&A.

## Features
- Web crawler for HTU content (English + Arabic)
- Chunking and extraction pipeline to JSONL corpus
- Embeddings with Sentence-Transformers (default: BAAI/bge-m3)
- Vector search with Qdrant (Dockerized)
- Optional reranking via cross-encoder
- Local LLM via Ollama
- FastAPI endpoint `/ask` and CLI query tool

## Architecture
- `src/crawler.py`, `src/selenium_crawler.py`, `src/static_content_crawler.py`: Crawl and fetch HTU pages
- `src/extract.py`, `src/chunker.py`: Clean and chunk text into JSONL
- `src/indexer_qdrant.py`: Build embeddings and index into Qdrant
- `src/rag_service_local.py`: Retrieve, rerank, and generate answer via Ollama
- `api/main.py`: FastAPI with `/ask` endpoint
- `query_system.py`: CLI client for testing queries
- `docker-compose.yml`: Qdrant + Ollama services

## Prerequisites
- Python 3.8+
- Docker and Docker Compose
- Git
- For Selenium crawler: Chrome/Chromium and matching ChromeDriver (Windows script provided)

## Quick Start

### 1) Clone and install
```bash
git clone https://github.com/Caractur/Chatbot-config-from-huggingFace-and-Docker.git
cd Chatbot-config-from-huggingFace-and-Docker
pip install -r requirements.txt
```

### 2) Start services (Qdrant + Ollama)
```bash
docker-compose up -d
```

### 3) (Optional) Pull Ollama models
```bash
# Windows
scripts/ollama_models.bat

# Linux/Mac
bash scripts/ollama_models.sh
```

### 4) Run API
```bash
cd api
uvicorn main:app --reload
# API at http://127.0.0.1:8000
```

### 5) Query examples (from project root)
```bash
# Interactive mode
python query_system.py

# One-off
python query_system.py "What programs does HTU offer?"

# Arabic
python query_system.py "ما هي البرامج التي تقدمها جامعة الحسين التقنية؟"
```

## Configuration

Create a `.env` in the project root (or use the defaults from `src/config.py`):

```env
# Crawling
ALLOWED_DOMAINS=htu.edu.jo
START_URLS=https://www.htu.edu.jo/,https://www.htu.edu.jo/ar/
CRAWL_MAX_PAGES=2000
CRAWL_RATE_SECONDS=0.6
USER_AGENT_NAME=HTUAssistantBot/1.0
USER_AGENT_EMAIL=you@example.com

# Embeddings & DB
EMBEDDING_MODEL=BAAI/bge-m3
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=htu-web
QDRANT_DISTANCE=Cosine

# LLM (Ollama)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M
MAX_TOKENS=700
TEMPERATURE=0.2

# Reranker
ENABLE_RERANKER=true
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
TOP_K=6
```

Tip: Provide `.env.example` in the repo and keep real `.env` out of git.

## API

- POST `/ask`
  - Body:
    ```json
    {
      "question": "What programs does HTU offer?",
      "top_k": 6,
      "lang": "en"
    }
    ```
  - Response:
    ```json
    {
      "answer": "…",
      "sources": ["https://www.htu.edu.jo/…", "…"]
    }
    ```

## Data
- Corpus file: `data/university_corpus.jsonl`
- By default, `data/` may be ignored by `.gitignore`. Remove that line if you want to commit datasets (not recommended for large files).

## Scripts
- `scripts/ollama_models.bat` / `.sh`: Pull recommended Ollama models
- `scripts/install_chromedriver.bat`: Install ChromeDriver (Windows)

## Troubleshooting
- “Connection refused” to Qdrant or Ollama: ensure `docker-compose up -d` and ports are free.
- “Model not found” in Ollama: run the model install script or `ollama pull <model>`.
- Long response times: reduce `TOP_K` or disable reranker.
- Windows newlines warnings: safe to ignore, or set `git config core.autocrlf true`.

## Project Structure
```
.
├── api/
│   └── main.py
├── data/
│   └── university_corpus.jsonl
├── scripts/
│   ├── install_chromedriver.bat
│   ├── ollama_models.bat
│   └── ollama_models.sh
├── src/
│   ├── config.py
│   ├── crawler.py
│   ├── selenium_crawler.py
│   ├── static_content_crawler.py
│   ├── extract.py
│   ├── chunker.py
│   ├── indexer_qdrant.py
│   ├── rag_service_local.py
│   └── ollama_client.py
├── docker-compose.yml
├── query_system.py
├── requirements.txt
└── README.md
```

## License
MIT
