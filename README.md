<div align="center">

# AIVera — Explainable Fake News Detection

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

[Key Features](#-key-features) • [Architecture](#-system-architecture) • [Model Fine-Tuning](#-model-fine-tuning--calibration) • [Security](#-security) • [API Reference](#-api-reference) • [Getting Started](#-getting-started) • [Browser Extension](#-browser-extension)

</div>

---

## 🌟 Key Features

### 🧠 Deep Credibility Analysis
- **RoBERTa Fine-Tuning**: High-accuracy sequence classification transformer (`roberta-base`) fine-tuned using PyTorch, Hugging Face `transformers` (`Trainer`), `datasets`, and `evaluate` on the WELFake dataset (72k+ articles, 95%+ validation accuracy).
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

## 🤖 Model Fine-Tuning & Calibration

The primary credibility classifier is a fine-tuned **RoBERTa** (`roberta-base`) model trained on full-length news articles. The end-to-end training and calibration process is scripted in [colab_training_distilbert.py](file:///d:/Study/projects/fake_news/fake_news/colab_training_distilbert.py).

### 🛠️ Frameworks & Tools Used
- **Base Architecture**: `roberta-base` (Hugging Face `AutoModelForSequenceClassification`)
- **Core Frameworks**: PyTorch (`torch`), Hugging Face `transformers` (`Trainer`, `TrainingArguments`), Hugging Face `datasets`, and `evaluate`.
- **Metrics & Calibration**: `scikit-learn` (`classification_report`, `confusion_matrix`, `LogisticRegression` for Platt scaling).
- **Hardware & Accelerators**: Google Colab GPU environment (NVIDIA T4 / A100 GPU) with CUDA and FP16 automatic mixed precision.

### 📊 Training Dataset
- **Dataset**: [WELFake Dataset](https://huggingface.co/datasets/ramielsayed/WELFake) — 72,134 labelled news articles (37,106 real news articles from Reuters, NYT, Guardian, AP; 35,028 fake news articles from PolitiFact, GossipCop, BuzzFeed, etc.).
- **Data Splits**: Stratified 80% Training / 10% Validation / 10% Held-Out Test split.
- **Preprocessing**: Article title and body combined (`title + " [SEP] " + text`), HTML tags stripped, normalized, and capped at 2,000 characters before tokenization.

### ⚙️ Training Setup & Hyperparameters
- **Tokenization**: `roberta-base` tokenizer with `MAX_LENGTH = 256`, dynamic padding, and truncation.
- **Loss Function & Class Weighting**: Custom `WeightedTrainer` applying inverse-frequency Class-Weighted Cross-Entropy Loss combined with **Label Smoothing** (`0.05`) to prevent overconfident softmax predictions.
- **Optimizer & Schedule**: AdamW optimizer with Cosine learning rate decay, learning rate `2e-5`, warmup ratio `0.06`, and weight decay `0.01`.
- **Batch Size**: 16 per device with 2 gradient accumulation steps (effective batch size = 32).
- **Epochs & Early Stopping**: Trained for 5 epochs with `EarlyStoppingCallback` (patience = 2 monitoring validation F1 score).

### 🎯 Post-Training Confidence Calibration (Platt Scaling)
Raw softmax outputs from transformer classifiers are often overconfident. A Platt scaling Logistic Regression model (`sklearn.linear_model.LogisticRegression`) is trained on validation set logit outputs:
$$p_{\text{calibrated}} = \frac{1}{1 + e^{A \cdot f(x) + B}}$$
The resulting calibration parameters ($\_A$ and $\_B$) are embedded in [calibration.py](file:///d:/Study/projects/fake_news/fake_news/ml-service/services/calibration.py) to transform raw inference output into calibrated probability scores.

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
This project was developed as part of an academic program.
