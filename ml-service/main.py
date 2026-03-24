"""
AIVera ML Service — FastAPI entry point.

Improvements implemented here:
- Input sanitization: HTML/script tags stripped before entering the NLP pipeline.
- Input length cap (50 000 chars) to prevent resource exhaustion.
- GET /health endpoint for Docker health-checks and gateway monitoring.
- GET /metrics endpoint via prometheus-fastapi-instrumentator.
- Structured per-request logging: input hash, prediction label, confidence,
  evidence sources hit, and latency per pipeline stage.
"""

import hashlib
import logging
import time
import re

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from services.nlp_service import segment_claims
from services.ocr_service import extract_text_from_image, extract_text_from_pdf
from services.ml_service import analyze_claim, has_model
from services.evidence_service import search_trusted_sources, compute_evidence_similarity
from services.url_service import extract_article_from_url
from services.cache_service import get_cached, set_cached
from models import ArticleAnalysisResponse, UrlExtractionRequest, UrlExtractionResponse
import uvicorn
import io

# ── Structured logging setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("aivera.ml")

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_INPUT_CHARS = 50_000   # ~12 000 tokens; hard cap before any processing

app = FastAPI(title="Fake News Detection ML Service", version="2.1.0")

# ── Prometheus metrics ────────────────────────────────────────────────────────
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    logger.info("[metrics] Prometheus instrumentator active — /metrics exposed.")
except ImportError:
    logger.warning("[metrics] prometheus-fastapi-instrumentator not installed. /metrics unavailable.")

# ── CORS: restrict to gateway + frontend only ─────────────────────────────────
# The ML service is an *internal* component. Only the Spring Boot gateway
# (localhost:8081) should call it. The browser/extension must NOT reach it
# directly; that path has no auth, no rate-limits, and no audit trail.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081"],   # gateway only — NOT "*"
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE   = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)
_STYLE_RE    = re.compile(r"<style[\s\S]*?</style>",   re.IGNORECASE)


def _sanitize_text(text: str) -> str:
    """
    Strip HTML/script/style tags from raw user input.
    This prevents:
    - Stored XSS when content is later displayed in the frontend.
    - Prompt-injection via HTML markup passed to the NLP tokenizer.
    """
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    # Normalize excess whitespace that tag removal can leave behind
    text = re.sub(r"\s{3,}", "\n\n", text).strip()
    return text


def _input_hash(text: str) -> str:
    """Return SHA-256 hex digest of normalized text (safe to log — no raw PII)."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


async def _run_analysis_pipeline(text: str) -> dict:
    """
    Core analysis pipeline shared by all input endpoints.
    Order of operations:
      1. Sanitize + length-check.
      2. Redis cache lookup (fast path).
      3. Claim segmentation (NLP).
      4. Per-claim: model inference + parallel evidence retrieval.
      5. Store result in cache.
    Emits structured log lines at each stage with latency measurements.
    """
    t0_total = time.perf_counter()
    h = _input_hash(text)

    # ── 1. Sanitize ───────────────────────────────────────────────────────────
    text = _sanitize_text(text)
    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Input exceeds maximum allowed length of {MAX_INPUT_CHARS} characters.",
        )

    # ── 2. Cache lookup ───────────────────────────────────────────────────────
    cached = get_cached(text)
    if cached:
        logger.info("[%s] cache=HIT  latency_total=0ms", h)
        return cached

    logger.info("[%s] cache=MISS  — running full pipeline", h)

    # ── 3. NLP claim segmentation ─────────────────────────────────────────────
    t_nlp = time.perf_counter()
    claims = segment_claims(text)
    nlp_ms = int((time.perf_counter() - t_nlp) * 1000)

    if not claims:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No declarative claims found in the provided text.",
        )

    analyzed_claims = []
    total_score = 0.0

    for claim in claims:
        # ── 4a. Model inference ───────────────────────────────────────────────
        t_model = time.perf_counter()
        base_score, explanation = analyze_claim(claim)
        model_ms = int((time.perf_counter() - t_model) * 1000)

        # ── 4b. Parallel evidence retrieval ───────────────────────────────────
        t_ev = time.perf_counter()
        evidence_snippets = await search_trusted_sources(claim)
        ev_ms = int((time.perf_counter() - t_ev) * 1000)

        claim_status = compute_evidence_similarity(claim, evidence_snippets)

        # ── 4c. Adjust score with evidence signal ──────────────────────────────
        final_score = base_score
        if claim_status == "SUPPORTED":
            final_score = min(final_score + 0.25, 1.0)
        elif claim_status == "CONTRADICTED":
            final_score = max(final_score - 0.25, 0.0)

        label = "REAL" if final_score >= 0.5 else "FAKE"
        logger.info(
            "[%s] claim_hash=%s  label=%s  score=%.4f  status=%s  "
            "nlp_ms=%d  model_ms=%d  evidence_ms=%d  evidence_count=%d",
            h, _input_hash(claim), label, final_score, claim_status,
            nlp_ms, model_ms, ev_ms, len(evidence_snippets),
        )

        analyzed_claims.append({
            "claim_text":        claim,
            "credibility_score": round(final_score, 6),
            "status":            claim_status,
            "evidence_snippets": evidence_snippets,
            "shap_explanation":  explanation,
        })
        total_score += final_score

    overall = total_score / len(claims)
    result = {
        "article_text":        text,
        "overall_credibility": round(overall, 6),
        "claims":              analyzed_claims,
    }

    total_ms = int((time.perf_counter() - t0_total) * 1000)
    logger.info(
        "[%s] pipeline=DONE  overall_score=%.4f  claims=%d  total_ms=%d",
        h, overall, len(claims), total_ms,
    )

    # ── 5. Cache (TTL 24 h) ───────────────────────────────────────────────────
    set_cached(text, result)

    return result


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """
    Health check consumed by Docker Compose and the Spring Boot gateway.
    Returns model load status so the gateway can back off if the model
    is still warming up on startup.
    """
    return {"status": "ok", "model_loaded": has_model}


@app.post("/analyze/text", response_model=ArticleAnalysisResponse)
async def analyze_text(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text provided for analysis.",
        )
    return await _run_analysis_pipeline(text)


@app.post("/analyze/file", response_model=ArticleAnalysisResponse)
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()

    if file.content_type == "application/pdf":
        text = extract_text_from_pdf(io.BytesIO(content))
    elif file.content_type in ["image/jpeg", "image/png", "image/jpg"]:
        text = extract_text_from_image(io.BytesIO(content))
    else:
        text = content.decode("utf-8")

    if not text or not text.strip():
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the uploaded file. Please upload a PDF or a clear image with readable text.",
        )

    return await _run_analysis_pipeline(text)


@app.post("/extract-url", response_model=UrlExtractionResponse)
async def extract_url(req: UrlExtractionRequest):
    # SSRF protection is enforced inside extract_article_from_url().
    # It raises HTTPException(400) for private/reserved addresses.
    title, text = extract_article_from_url(req.url)
    return {"title": title, "text": text}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
