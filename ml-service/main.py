from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from services.nlp_service import segment_claims
from services.ocr_service import extract_text_from_image, extract_text_from_pdf
from services.ml_service import analyze_claim
from services.evidence_service import search_trusted_sources, compute_evidence_similarity
from services.url_service import extract_article_from_url
from services.cache_service import get_cached, set_cached        # Feature 2: Redis cache
from models import ArticleAnalysisResponse, UrlExtractionRequest, UrlExtractionResponse
import uvicorn
import io

app = FastAPI(title="Fake News Detection ML Service")

# Feature 3: Restrict CORS to the Spring Boot gateway only.
# The ML service is an internal component and must not be directly accessible
# from the browser or external clients. All traffic must go through the gateway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081"],   # gateway only — NOT "*"
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


async def _run_analysis_pipeline(text: str) -> dict:
    """
    Core analysis pipeline shared by text and file endpoints.
    Checks Redis cache first (Feature 2) and delegates to ML + evidence services.
    """
    # ── Feature 2: cache lookup ────────────────────────────────────────────────
    cached = get_cached(text)
    if cached:
        print("[cache] HIT — returning cached result")
        return cached

    print("[cache] MISS — running full pipeline")

    claims = segment_claims(text)
    if not claims:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No declarative claims found in the provided text.",
        )

    analyzed_claims = []
    total_score = 0.0

    for claim in claims:
        # ── ML inference + SHAP (Feature 4 calibration applied inside ml_service) ──
        base_score, explanation = analyze_claim(claim)

        # ── Feature 1: evidence sources fetched in parallel (async) ──────────────
        evidence_snippets = await search_trusted_sources(claim)
        claim_status = compute_evidence_similarity(claim, evidence_snippets)

        # Apply evidence weightage to calibrated score
        final_score = base_score
        if claim_status == "SUPPORTED":
            final_score = min(final_score + 0.25, 1.0)
        elif claim_status == "CONTRADICTED":
            final_score = max(final_score - 0.25, 0.0)

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

    # ── Feature 2: store in cache (TTL 24h) ───────────────────────────────────
    set_cached(text, result)

    return result


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
    title, text = extract_article_from_url(req.url)
    return {"title": title, "text": text}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
