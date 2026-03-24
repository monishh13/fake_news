<div align="center">

# AIVera — Explainable Fake News Detection

<a href="https://github.com/monishh13/fake_news/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/monishh13/fake_news" />
</a>
<a href="#">
    <img alt="Backend" src="https://img.shields.io/badge/Backend-Spring%20Boot-green" />
</a>
<a href="#">
    <img alt="ML" src="https://img.shields.io/badge/ML%20Service-FastAPI-blue" />
</a>
<a href="#">
    <img alt="Model" src="https://img.shields.io/badge/Model-RoBERTa-orange" />
</a>
<a href="#">
    <img alt="Security" src="https://img.shields.io/badge/Security-SSRF%20Protected-red" />
</a>

<br><br>

AIVera is a secure, full-stack AI ecosystem for misinformation detection through deep credibility analysis and transparent explainability. It analyzes individual claims with a high-accuracy fine-tuned RoBERTa transformer, verifies them against multiple live evidence sources, and explains every prediction with word-level SHAP attributions.

---

[Key Features](#-key-features) • [Architecture](#-system-architecture) • [Security](#-security) • [API Reference](#-api-reference) • [Getting Started](#-getting-started) • [Browser Extension](#-browser-extension)

</div>

---

## 🌟 Key Features

### 🧠 Deep Credibility Analysis
- **RoBERTa Scoring**: High-accuracy transformer model fine-tuned on the WELFake dataset for misinformation detection (95%+ validation accuracy).
- **Calibrated Confidence**: Platt scaling applied to raw softmax output — scores are genuinely calibrated probabilities, not overconfident logit values.
- **Claim Segmentation**: Long-form text, PDFs, and images are automatically broken into individual declarative claims for granular verification.

### 🔍 Multi-Source Evidence Retrieval (Parallel)
All sources are fetched concurrently via `asyncio.gather()` — total latency is the *max* of individual latencies, not their sum:

| Source | Type | Limit |
|--------|------|-------|
| Google Fact Check API | Structured fact-checks | Generous free tier |
| Wikipedia (semantic search) | Background context | Unlimited |
| NewsAPI / NewsData.io | Recent news articles | 100–200 req/day |
| **GDELT (fallback)** | Global news graph | **Free & unlimited** |

Every evidence snippet is tagged with a **domain credibility score** (Reuters = 1.0, unknown = 0.6) so high-quality sources carry more weight.

### 📊 Explainable AI (XAI) with Uncertainty Communication
- **SHAP Integration**: Word-level attribution bar charts showing exactly which tokens pushed the score towards Real or Fake.
- **Uncertainty Banner**: When a claim score is between 0.35–0.65, an explicit amber warning is shown: *"Low confidence — treat this result with caution."*
- **SHAP Disclaimer**: Clear caveat that attributions are indicative only and may be unreliable on political/satire content.

### 🛡️ Security-First Design
- **SSRF Protection**: URL extraction validates scheme, resolves hostname DNS, and blocks all RFC 1918 / loopback / AWS metadata (169.254.x.x) addresses.
- **Input Sanitization**: HTML and `<script>` tags stripped from all user input before NLP processing or database storage.
- **Rate Limiting**: Per-IP rate limiting on the Spring Boot gateway (60 req/min default).
- **CORS Lockdown**: ML service accepts requests only from the gateway (`localhost:8081`); frontend CORS restricted to known origins.

### 🖼️ OCR & Multi-Format Input
- Supports **PDF documents**, **PNG/JPG images**, and raw text paste.
- Integrated **Tesseract OCR** for analyzing social media screenshots.
- URL scraping with SSRF-safe article extraction.

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│   React Dashboard (Vite)        Chrome/Edge Extension           │
└──────────────────────┬────────────────────┬─────────────────────┘
                       │ HTTP               │ HTTP (via gateway)
                       ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              SPRING BOOT GATEWAY  :8081                         │
│  • Rate limiting (60 req/min/IP)  • CORS enforcement            │
│  • Analysis persistence (H2/PostgreSQL)  • History API          │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Internal HTTP only
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              FASTAPI ML SERVICE  :8000                          │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │ spaCy NLP │ │ RoBERTa   │ │   SHAP   │ │Evidence Retrieval│  │
│  │ Segmenter │ │+ Platt Cal│ │ XAI      │ │(parallel async) │  │
│  └───────────┘ └───────────┘ └──────────┘ └────────┬────────┘  │
│                                                     │            │
│  ┌──────────┐  ┌────────────────────────────────────┤            │
│  │  Redis   │  │  Wikipedia  │ Fact Check │ GDELT   │           │
│  │  Cache   │  │  (semantic) │  (Google)  │(fallbk) │           │
│  └──────────┘  └────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

The browser extension routes **through the Spring Boot gateway** — the ML service is never directly exposed to the browser.

---

## 🔒 Security

### SSRF Protection
`POST /extract-url` validates every submitted URL before fetching:
- Only `http` and `https` schemes allowed.
- Hostname resolved via DNS; IP checked against blocked ranges.
- Blocked: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16` (AWS metadata), `100.64.0.0/10`.

### Input Sanitization
All text inputs are sanitized before processing:
- `<script>` and `<style>` blocks stripped entirely.
- All remaining HTML tags removed via regex.
- Hard limit: **50,000 characters** (HTTP 413 if exceeded).

### Rate Limiting
The Spring Boot `ApiKeyInterceptor` enforces per-IP rate limits (default: 60 req/min). Authenticated clients (via `X-API-KEY` header) can bypass IP-level throttling.

---

## 📡 API Reference

### ML Service  (`:8000` — internal only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze/text` | Analyze plain text (form-encoded) |
| `POST` | `/analyze/file` | Analyze PDF or image upload |
| `POST` | `/extract-url` | SSRF-protected article extraction |
| `GET`  | `/health` | Health check (`{"status":"ok","model_loaded":true}`) |
| `GET`  | `/metrics` | Prometheus metrics endpoint |

### Backend Gateway  (`:8081` — public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/detection/text` | Analyze text (proxied + persisted) |
| `POST` | `/api/detection/file` | Analyze file (proxied + persisted) |
| `POST` | `/api/detection/extract-url` | SSRF-safe URL extraction |
| `GET`  | `/api/detection/history` | Fetch all saved analyses |
| `GET`  | `/api/detection/{id}` | Fetch a specific report by ID |

---

## 🔬 Observability

### Structured Logging
Every request is logged with:
- **Input hash** (SHA-256 of normalized text — no raw PII)
- **Prediction label** (REAL / FAKE) and **calibrated confidence**
- **Per-stage latency** (NLP segmentation, model inference, evidence retrieval)
- **Evidence source count** per claim

```
[a3f2b1c8] cache=MISS — running full pipeline
[a3f2b1c8] claim_hash=d4e5f6a7  label=FAKE  score=0.3241  nlp_ms=45  model_ms=312  evidence_ms=891
[a3f2b1c8] pipeline=DONE  overall_score=0.3241  claims=1  total_ms=1248
```

### Prometheus Metrics
`GET /metrics` exposes request counts, latency histograms, and error rates in Prometheus text format. Compatible with Grafana dashboards out of the box.

---

## ⚙️ Getting Started

### Prerequisites
- **Node.js** v18+
- **Java JDK 17+**
- **Python 3.10+**
- **Tesseract OCR** (must be in system PATH)
- **Redis** (optional — caching degrades gracefully without it)

### 1. Configure Environment Variables

Copy and fill in the template:
```bash
cp ml-service/.env.example ml-service/.env
```

```env
GOOGLE_API_KEY=your_google_fact_check_api_key
NEWS_API_KEY=your_newsapi_or_newsdata_key   # optional — GDELT is free fallback
REDIS_HOST=localhost
REDIS_PORT=6379
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

> **Note**: If `NEWS_API_KEY` is not set, AIVera automatically falls back to GDELT, which is free with no daily limit.

### 2. Quick Start (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```
Launches all services: ML service → Spring Boot → React dev server. (Automatically downloads and configures Maven if missing).

### 3. Automated Testing
You can run the end-to-end integration test against the live API to verify claim analysis, SHAP evidence, and NLI status:
```bash
cd ml-service
python test_pipeline.py
```

### 3. Docker Compose (All services including Redis)
```bash
docker compose up --build
```
Services: `postgres`, `redis`, `ml-service` (with healthcheck), `backend`, `frontend`.

### 4. Manual Start
```bash
# ML Service
cd ml-service && pip install -r requirements.txt
python main.py          # http://localhost:8000

# Backend (new terminal)
cd backend && mvn spring-boot:run    # http://localhost:8081

# Frontend (new terminal)
cd frontend && npm install && npm run dev    # http://localhost:5173
```

---

## 🔌 Browser Extension

The Chrome/Edge extension routes **all requests through the Spring Boot gateway** (not directly to the ML service), ensuring:
- Rate limiting and authentication apply to extension traffic.
- No ML service URL is exposed to the browser.

**Setup**: Load `extension/` as an unpacked extension in `chrome://extensions`.

**Usage**:
1. Highlight any text on any webpage.
2. Right-click → *Analyze with AIVera*.
3. View credibility score, evidence snippets, and status badge in the popup.
4. Click *Open Full Dashboard* to see the complete SHAP analysis.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
