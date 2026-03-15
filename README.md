<div align="center">

# <img src="docs/logo-placeholder.png" width="40" alt="AIVera Logo" /> AIVera - Explainable Fake News Detection

<a href="https://github.com/monishh13/fake_news/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/monishh13/fake_news" />
</a>
<a href="https://github.com/monishh13/fake_news/stargazers">
    <img alt="Stars" src="https://img.shields.io/github/stars/monishh13/fake_news?style=social" />
</a>
<a href="#">
    <img alt="Backend" src="https://img.shields.io/badge/Backend-Spring%20Boot-green" />
</a>
<a href="#">
    <img alt="ML" src="https://img.shields.io/badge/ML%20Service-FastAPI-blue" />
</a>

<br><br>

AIVera is an advanced, full-stack AI ecosystem designed to combat misinformation through deep credibility analysis and transparent explainability.

---

[Key Features](#-key-features) • [System Architecture](#-system-architecture) • [Browser Extension](#-browser-extension) • [Getting Started](#-getting-started)

</div>

## 🌟 Key Features

### 🧠 Deep Credibility Analysis
- **DistilBERT-powered Scoring**: Evaluates individual claims using a custom-trained Transformer model optimized for high-precision misinformation detection.
- **Claim Segmentation**: Automatically breaks down long-form text, PDFs, or images into separate declarative claims for granular verification.

### 🔍 Multi-Source Evidence Retrieval
AIVera doesn't just predict; it verifies. Our evidence engine cross-references claims against:
- **Google Fact Check Tools API**: Fetches results from verified fact-checkers globally.
- **Wikipedia (Live Search)**: Dynamically retrieves relevant context using Semantic Similarity (`all-MiniLM-L6-v2`).
- **NewsAPI.org**: Pulls recent news descriptions for real-time contextual evidence.

### 📊 Explainable AI (XAI)
- **SHAP Integration**: Provides word-level attribution charts. See exactly which phrases (e.g., "Death Rumors", "AI-generated") influenced the AI's final score.
- **Confidence Metrics**: Transparent scoring system weighted by retrieved evidence.

### 🖼️ OCR & File Support
- Supports **PDF documents**, **PNG/JPG images**, and raw text pastes.
- Integrated **Tesseract OCR** for analyzing screenshots of social media posts or news snippets.

---

## 🏗 System Architecture

The project follows a robust microservice-oriented 3-tier architecture:

### 1. Frontend (React + Vite)
- **Tech**: React 18, Vite, Lucide, Recharts.
- **Capabilities**: Interactive dashboard, live history archive, dark/light theme toggle, and rich SHAP visualizations.

### 2. Backend Gateway (Spring Boot)
- **Tech**: Java 17, Spring Boot, Spring Data JPA, H2/MySQL.
- **Capabilities**: Central API gateway, analysis persistence, history management, and proxying to the ML service.

### 3. ML Service (FastAPI)
- **Tech**: Python 3.10, FastAPI, PyTorch, HuggingFace, spaCy, SHAP.
- **Capabilities**: Heavy NLP processing, claim extraction, model inference, and multi-source evidence fetching.

---

## 🔌 Browser Extension

AIVera includes a **Chrome/Edge Extension** for real-time analysis while browsing:
- **Right-Click Analysis**: Highlight any text on any website and analyze it instantly.
- **Integrated Evidence**: View credibility scores and supporting/contradicting evidence snippets directly in the extension popup.
- **Deep Dive**: One-click access from the extension to the full dashboard for detailed SHAP impact analysis.

---

## ⚙️ Getting Started

### Requirements
- **Node.js** (v18+)
- **Java JDK 17+**
- **Python 3.10+**
- **Tesseract OCR** (Ensure `tesseract` is in your system PATH)

### API Keys
Create a `.env` file in the `ml-service/` directory:
```env
GOOGLE_API_KEY=your_google_fact_check_api_key
NEWS_API_KEY=your_news_api_key
```

### Quick Start (Windows)
Run the automated launcher from the root directory:
```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```
This script handles dependency installation and launches all three service layers automatically.

---

## 📸 Screenshots

| Feature | Description |
|---------|-------------|
| **Analyze Center** | Central hub for uploading and viewing claim weightage. |
| **Explainability** | Detailed SHAP charts showing word-level impact. |
| **Evidence Panel** | Real-world verification from Wikipedia and Google Fact Check. |
| **Extension** | Quick-access tool for analyzing browser selections. |

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
