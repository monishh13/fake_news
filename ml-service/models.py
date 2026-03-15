from pydantic import BaseModel
from typing import List, Optional

class ClaimAnalysis(BaseModel):
    claim_text: str
    credibility_score: float
    status: str # SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE
    evidence_snippets: List[str]
    shap_explanation: dict # word/phrase mapping to importance score

class ArticleAnalysisResponse(BaseModel):
    article_text: str
    overall_credibility: float
    claims: List[ClaimAnalysis]

class UrlExtractionRequest(BaseModel):
    url: str

class UrlExtractionResponse(BaseModel):
    title: str
    text: str
