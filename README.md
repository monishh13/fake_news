# AIVera - Explainable Fake News Detection

AIVera is a full-stack, AI-powered credibility analysis and fake news detection system. Unlike traditional binary truth classifiers, AIVera segments long-form text into individual declarative claims, evaluates the credibility of each claim using a fine-tuned Transformer model (DistilBERT), and provides **transparent, word-level explanations** using SHAP (SHapley Additive exPlanations).

Additionally, AIVera integrates with live data sources (Wikipedia) and uses Semantic Similarity (SentenceTransformers) to retrieve and display real-world evidence confirming or contradicting the analyzed claims.

---

## 🏗 System Architecture

The project is structured as a modern 3-tier microservice architecture:

### 1. Frontend (React + Vite)
- **Location**: `frontend/`
- **Stack**: React, Vite, Lucide React (Icons), Recharts (Data Visualization).
- **Features**:
  - Clean, dark-themed responsive UI with Dark/Light mode toggle.
  - Multi-input support: Paste text directly or upload/drag-and-drop documents (`.txt`, `.pdf`, `.png`, `.jpg`).
  - Interactive SHAP charts showing exactly which words in a sentence pushed the AI toward a "Fake" or "Real" prediction.
  - Local caching of analysis history.

### 2. Backend (Spring Boot + Java)
- **Location**: `backend/`
- **Stack**: Java 17, Spring Boot, Spring Data JPA, H2 In-Memory Database (easily swappable to MySQL).
- **Features**:
  - Serves as the central API Gateway for the frontend.
  - Handles file uploads using `MultipartFile`.
  - Persists analyzed articles and individual mapped claims to the SQL database to prevent infinite re-analysis.
  - Proxies complex NLP calls to the Python ML Microservice.

### 3. ML Microservice (Python + FastAPI)
- **Location**: `ml-service/`
- **Stack**: Python 3, FastAPI, PyTorch, HuggingFace Transformers, spaCy, SHAP, Wikipedia-API.
- **Features**:
  - **OCR & PDF Extraction**: Uses `pytesseract` to read image text and `PyPDF2` to read documents.
  - **Claim Segmentation**: Uses NLP (`spaCy`) to split paragraphs into declarative statements, ignoring questions or greetings.
  - **DistilBERT Inference**: Uses a HuggingFace pipeline locally to score the credibility of claims.
  - **Explainable AI (XAI)**: Uses `shap.Explainer` to calculate the exact attribution/weight of every token in the input text.
  - **Evidence Retrieval**: Pulls the top keywords from a claim, searches Wikipedia live, grabs summary paragraphs, and uses `SentenceTransformers` (`all-MiniLM-L6-v2`) to mathematically find the most semantically relevant sentences to display as "Evidence".

---

## 🚀 How It Works (The Pipeline)

1. **Input**: A user pastes a news article or uploads a PDF screenshot of a tweet.
2. **Gateway**: The Spring Boot backend accepts the request, saves the raw file, and asks the ML Microservice to extract text.
3. **Segmentation**: The ML service breaks the text down (e.g., extracting 3 distinct claims from a 2-paragraph article).
4. **Scoring & SHAP**: Each claim is fed to DistilBERT. DistilBERT returns a Real/Fake probability score. SHAP analyzes DistilBERT's brain and outputs a chart showing *why* it gave that score. 
5. **Fact Retrieval**: Keywords from the claim are queried against Wikipedia. The AI reads the top Wikipedia articles, finds sentences with the highest semantic similarity to the original claim, and attaches them as evidence.
6. **Result**: The Spring Boot app saves everything to the database and returns a beautiful JSON payload to the React frontend to render for the user.

---

## ⚙️ Running the Project

The easiest way to run the entire stack locally on Windows is to use the provided `start.ps1` Powershell script in the root directory.

### Requirements
- Node.js (v18+)
- Java JDK 17+ and Maven
- Python 3.10+
- Tesseract OCR (Installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` for image uploads)

### Start all services
```powershell
# Run from the root directory
powershell -ExecutionPolicy Bypass -File .\start.ps1
```
This script will automatically install missing dependencies (npm modules, pip packages) and launch 3 separate windows for the Frontend, Backend, and ML Service. 

You can access the UI at **http://localhost:5173**.
