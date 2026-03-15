from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from services.nlp_service import segment_claims
from services.ocr_service import extract_text_from_image, extract_text_from_pdf
from services.ml_service import analyze_claim
from services.evidence_service import search_trusted_sources, compute_evidence_similarity
from services.url_service import extract_article_from_url
from models import ArticleAnalysisResponse, UrlExtractionRequest, UrlExtractionResponse
import uvicorn
import io

app = FastAPI(title="Fake News Detection ML Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze/text", response_model=ArticleAnalysisResponse)
async def analyze_text(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text provided for analysis."
        )

    claims = segment_claims(text)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No declarative claims found in the provided text."
        )

    analyzed_claims = []
    total_score = 0
    
    for claim in claims:
        # Get distilbert prediction & shap explanation
        base_score, explanation = analyze_claim(claim)
        
        # Retrieve evidence and determine status
        evidence_snippets = search_trusted_sources(claim)
        status = compute_evidence_similarity(claim, evidence_snippets)
        
        # Apply evidence weightage to credibility score
        final_score = base_score
        if status == "SUPPORTED":
            final_score = min(final_score + 0.25, 1.0)
        elif status == "CONTRADICTED":
            final_score = max(final_score - 0.25, 0.0)
        
        analyzed_claims.append({
            "claim_text": claim,
            "credibility_score": final_score,
            "status": status,
            "evidence_snippets": evidence_snippets,
            "shap_explanation": explanation
        })
        total_score += final_score
        
    overall = total_score / len(claims)
        
    return {
        "article_text": text,
        "overall_credibility": overall,
        "claims": analyzed_claims
    }

@app.post("/analyze/file", response_model=ArticleAnalysisResponse)
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()

    if file.content_type == "application/pdf":
        text = extract_text_from_pdf(io.BytesIO(content))
    elif file.content_type in ["image/jpeg", "image/png", "image/jpg"]:
        text = extract_text_from_image(io.BytesIO(content))
    else:
        text = content.decode('utf-8')

    # If OCR/pdf extraction produced no text, inform the caller.
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the uploaded file. Please upload a PDF or a clear image with readable text."
        )

    return await analyze_text(text=text)

@app.post("/extract-url", response_model=UrlExtractionResponse)
async def extract_url(req: UrlExtractionRequest):
    title, text = extract_article_from_url(req.url)
    return {"title": title, "text": text}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
