from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from models import ArticleAnalysisResponse
from services.ocr_service import extract_text_from_image, extract_text_from_pdf
from services.nlp_service import segment_claims
from services.ml_service import analyze_claim
from services.evidence_service import search_trusted_sources, compute_evidence_similarity
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
    claims = segment_claims(text)
    
    analyzed_claims = []
    total_score = 0
    
    for claim in claims:
        # Get distilbert prediction & shap explanation
        score, explanation = analyze_claim(claim)
        
        # Retrieve evidence and determine status
        evidence_snippets = search_trusted_sources(claim)
        status = compute_evidence_similarity(claim, evidence_snippets)
        
        analyzed_claims.append({
            "claim_text": claim,
            "credibility_score": score,
            "status": status,
            "evidence_snippets": evidence_snippets,
            "shap_explanation": explanation
        })
        total_score += score
        
    overall = total_score / len(claims) if claims else 0.5
        
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
        
    return await analyze_text(text=text)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
