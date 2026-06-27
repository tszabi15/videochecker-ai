# VideoChecker AI — Production-Grade Video Quality Auditor

An end-to-end automated educational video quality analysis application powered by **Google Gemini 3.1 Pro Preview** and **OpenAI Whisper large-v3**.

---

## Architecture Overview

```
                      +-------------------+
                      |   React 18 SPA    |
                      |   (Vite + TS)     |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      |   FastAPI REST    |
                      |    (API V1)       |
                      +----+--------+-----+
                           |        |
           +---------------+        +---------------+
           |                                        |
           v                                        v
  +------------------+                    +------------------+
  |  PostgreSQL 15   |                    |     Redis 7      |
  | (Job Persistence)|                    | (Celery Broker)  |
  +------------------+                    +--------+---------+
                                                   |
                                                   v
                                          +------------------+
                                          |  Celery Worker   |
                                          | (5-Stage Task)   |
                                          +--------+---------+
                                                   |
                        +--------------------------+--------------------------+
                        |                          |                          |
                        v                          v                          v
             +--------------------+      +--------------------+      +--------------------+
             |  FFmpeg Processing |      | OpenAI Whisper API |      | Gemini File API &  |
             | (1fps, 1080p, WAV) |      | (Word Timestamps)  |      | Structured Schema  |
             +--------------------+      +--------------------+      +--------------------+
```

### Celery 5-Stage Pipeline Workflow
1. **Stage 1 — Preprocess**: Video normalization (max 1080p), 1fps frame extraction to JPEG, 16kHz mono WAV audio extraction, MD5 checksum calculation.
2. **Stage 2 — Transcribe**: Whisper large-v3 transcription with per-word timestamp alignment.
3. **Stage 3 — Analyze**: Gemini File API upload, dynamic prompt execution against mandatory quality checklist (A-G), structured JSON generation via Pydantic response schema.
4. **Stage 4 — Validate**: Cross-validation of reported audio issues against Whisper transcript & secondary verification calls for CRITICAL findings.
5. **Stage 5 — Finalize**: Result consolidation, score calculations, Markdown report synthesis, DB state updates to `DONE`.

---

## Cost Estimation Guide per Model

The application tracks token usage precisely and applies long-context tiers automatically.

| Model Tier | Base Input Rate (per 1M) | Base Output Rate (per 1M) | Long-Context Tier (>200K Tokens) | Batch Mode Discount |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.1 Pro** | $2.00 | $12.00 | $4.00 In / $18.00 Out | 50% Off |
| **Gemini 3.5 Flash** | $1.50 | $9.00 | $1.50 In / $9.00 Out | 50% Off |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | $0.30 In / $2.50 Out | 50% Off |

### Example Cost Calculation Formula
For a 10-minute (600s) HD video analyzed with Gemini 3.1 Pro:
- **Estimated Input Tokens**: ~185,000 tokens (Standard Tier)
- **Estimated Output Tokens**: ~2,500 tokens
- **Realtime Cost**: `(185,000 / 1,000,000 * $2.00) + (2,500 / 1,000,000 * $12.00)` = **$0.40 USD**
- **Batch Mode Cost**: **$0.20 USD**

---

## Setup & Local Development

### 1. Prerequisites
- Docker & Docker Compose installed locally
- Python 3.11+ (for running pytest natively)

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 3. Launch with Docker Compose
```bash
docker-compose up --build
```
Access points:
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Running Pytest Suite
```bash
pip install -r backend/requirements.txt
pytest tests/
```
