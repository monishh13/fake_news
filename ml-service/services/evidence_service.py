"""
Evidence Service — parallel retrieval from Wikipedia, Google Fact Check,
NewsAPI/NewsData, and GDELT (free fallback).

Key improvements:
- GDELT added as a free, unlimited fallback when NewsAPI returns no results.
- Source credibility scoring: evidence is tagged with a quality weight so
  the caller can distinguish Reuters (1.0) from unknown tabloids (0.4).
- All remote calls remain parallel via asyncio.gather().
"""

import asyncio
import httpx
import torch
import os
import wikipedia
import spacy
from sentence_transformers import SentenceTransformer, util
from dotenv import load_dotenv

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

try:
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print("Warning: unable to load SentenceTransformer for evidence service", e)
    embedder = None

load_dotenv()

GOOGLE_FACT_CHECK_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

# ── Source credibility registry ───────────────────────────────────────────────
# Based on internationally recognised journalistic standards.
# Key = lowercased domain or source name fragment; Value = 0.0–1.0 credibility.
_DOMAIN_CREDIBILITY: dict[str, float] = {
    # Premium / wire services
    "reuters":    1.0,
    "ap news":    1.0,
    "apnews":     1.0,
    "bbc":        0.95,
    "npr":        0.95,
    "theguardian":0.92,
    "guardian":   0.92,
    "nytimes":    0.90,
    "washingtonpost": 0.90,
    "economist":  0.90,
    # Science / fact-check
    "snopes":     0.90,
    "politifact": 0.90,
    "factcheck":  0.90,
    "science":    0.85,
    # Mid-tier
    "cnn":        0.75,
    "fox":        0.65,
    "dailymail":  0.45,
    "nypost":     0.50,
    "buzzfeed":   0.55,
}
_DEFAULT_CREDIBILITY = 0.60  # unknown sources get a conservative default


def _credibility_for_source(source_name: str) -> float:
    """Return a 0–1 credibility score for a publication name."""
    lower = source_name.lower()
    for key, score in _DOMAIN_CREDIBILITY.items():
        if key in lower:
            return score
    return _DEFAULT_CREDIBILITY


def extract_keywords_entities(text: str) -> list[str]:
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents]
    keywords = [chunk.text for chunk in doc.noun_chunks]
    return list(set(entities + keywords))


# ── Async helpers for each source ─────────────────────────────────────────────

async def _fetch_google_fact_check(client: httpx.AsyncClient, query: str) -> list[str]:
    """Call Google Fact Check Tools API asynchronously."""
    if not GOOGLE_FACT_CHECK_API_KEY:
        return []
    try:
        res = await client.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={"query": query, "key": GOOGLE_FACT_CHECK_API_KEY},
            timeout=6,
        )
        if res.status_code == 200:
            data = res.json()
            snippets = []
            for c in data.get("claims", [])[:2]:
                reviews = c.get("claimReview", [])
                if reviews:
                    review = reviews[0]
                    publisher = review.get("publisher", {}).get("name", "Fact-checker")
                    rating = review.get("textualRating", "Unknown")
                    cred = _credibility_for_source(publisher)
                    snippets.append(
                        f"[Google Fact Check] {publisher} rating: {rating}. "
                        f"Original claim: {c.get('text', '')} "
                        f"[credibility:{cred:.2f}]"
                    )
            return snippets
        else:
            print(f"Google Fact Check API Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Google Fact Check API error: {e}")
    return []


async def _fetch_news_api(client: httpx.AsyncClient, query: str) -> list[str]:
    """Call NewsAPI / NewsData asynchronously."""
    if not NEWS_API_KEY:
        return []
    try:
        if NEWS_API_KEY.startswith("pub_"):
            # NewsData.io
            res = await client.get(
                "https://newsdata.io/api/1/news",
                params={"q": query, "apikey": NEWS_API_KEY, "language": "en"},
                timeout=6,
            )
            if res.status_code == 200:
                data = res.json()
                snippets = []
                for art in data.get("results", [])[:3]:
                    desc = art.get("description") or art.get("content")
                    if desc and len(desc) > 20:
                        source = art.get("source_id", "News")
                        cred = _credibility_for_source(source)
                        snippets.append(
                            f"[NewsData - {source}] {desc[:300].strip()} "
                            f"[credibility:{cred:.2f}]"
                        )
                return snippets
            else:
                print(f"NewsData.io Error ({res.status_code}): {res.text}")
        else:
            # NewsAPI.org
            res = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query, "apiKey": NEWS_API_KEY,
                    "language": "en", "sortBy": "relevancy", "pageSize": 3
                },
                timeout=6,
            )
            if res.status_code == 200:
                data = res.json()
                snippets = []
                for art in data.get("articles", []):
                    desc = art.get("description")
                    if desc and len(desc) > 20:
                        source_name = art.get("source", {}).get("name", "News")
                        cred = _credibility_for_source(source_name)
                        snippets.append(
                            f"[NewsAPI - {source_name}] {desc.strip()} "
                            f"[credibility:{cred:.2f}]"
                        )
                return snippets
            else:
                print(f"NewsAPI Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"News API error: {e}")
    return []


async def _fetch_gdelt(client: httpx.AsyncClient, query: str) -> list[str]:
    """
    Fetch news results from GDELT GKG (Global Knowledge Graph).
    GDELT is completely free with no daily request limits — used as a
    fallback when NewsAPI is unavailable or has exceeded its quota.
    """
    try:
        res = await client.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query":      query,
                "mode":       "ArtList",
                "maxrecords": 5,
                "format":     "json",
            },
            timeout=8,
        )
        if res.status_code == 200:
            data = res.json()
            snippets = []
            for art in (data.get("articles") or [])[:3]:
                title = art.get("title", "").strip()
                domain = art.get("domain", "gdelt")
                if title and len(title) > 10:
                    cred = _credibility_for_source(domain)
                    snippets.append(
                        f"[GDELT - {domain}] {title} [credibility:{cred:.2f}]"
                    )
            return snippets
        else:
            print(f"GDELT API Error ({res.status_code})")
    except Exception as e:
        print(f"GDELT API error: {e}")
    return []


def _fetch_wikipedia_sync(query: str) -> list[str]:
    """Fetch Wikipedia snippets synchronously (library is sync-only)."""
    try:
        snippets = []
        search_results = wikipedia.search(query, results=2)
        for title in search_results:
            try:
                summary = wikipedia.summary(title, sentences=3, auto_suggest=False)
                sentences = [
                    f"[Wikipedia] {s.text.strip()}"
                    for s in nlp(summary).sents
                    if len(s.text.strip()) > 20
                ]
                snippets.extend(sentences)
            except wikipedia.exceptions.DisambiguationError as e:
                try:
                    summary = wikipedia.summary(e.options[0], sentences=2, auto_suggest=False)
                    sentences = [
                        f"[Wikipedia] {s.text.strip()}"
                        for s in nlp(summary).sents
                        if len(s.text.strip()) > 20
                    ]
                    snippets.extend(sentences)
                except Exception:
                    pass
            except Exception:
                pass
        return snippets
    except Exception as e:
        print(f"Wikipedia search failed: {e}")
        return []


# ── Public async interface ────────────────────────────────────────────────────

async def search_trusted_sources(claim: str) -> list[str]:
    """
    Retrieve evidence snippets from all sources **in parallel**.
    Total latency ≈ max(individual latencies) instead of their sum.

    GDELT is fired concurrently with the other sources and its results are
    included when NewsAPI returns no usable snippets (free unlimited fallback).
    """
    if not embedder:
        return []

    keywords = extract_keywords_entities(claim)
    if not keywords:
        keywords = [t.text for t in nlp(claim) if not t.is_stop and t.is_alpha][:5]
    if not keywords:
        keywords = claim.split()[:5]

    query = " ".join(keywords[:3])

    # Fire all four sources concurrently
    loop = asyncio.get_event_loop()
    async with httpx.AsyncClient() as client:
        google_task = _fetch_google_fact_check(client, query)
        news_task   = _fetch_news_api(client, query)
        gdelt_task  = _fetch_gdelt(client, query)
        wiki_task   = loop.run_in_executor(None, _fetch_wikipedia_sync, query)

        google_snippets, news_snippets, gdelt_snippets, wiki_snippets_raw = await asyncio.gather(
            google_task, news_task, gdelt_task, wiki_task
        )

    # Use GDELT only when NewsAPI/NewsData returned nothing
    final_news = news_snippets if news_snippets else gdelt_snippets

    # Semantic filter on Wikipedia results only
    filtered_wiki: list[str] = []
    if wiki_snippets_raw and embedder:
        claim_emb = embedder.encode(claim, convert_to_tensor=True)
        evidence_embs = embedder.encode(wiki_snippets_raw, convert_to_tensor=True)
        cosine_scores = util.cos_sim(claim_emb, evidence_embs)[0]
        top_k = min(3, len(wiki_snippets_raw))
        top_results = torch.topk(cosine_scores, k=top_k)
        for score, idx in zip(top_results[0], top_results[1]):
            if score.item() > 0.10:
                filtered_wiki.append(wiki_snippets_raw[idx])

    return google_snippets + final_news + filtered_wiki


def compute_evidence_similarity(claim: str, evidence: list[str]) -> str:
    """Determine whether the claim is SUPPORTED, CONTRADICTED, or INSUFFICIENT_EVIDENCE."""
    if not evidence or not embedder:
        return "INSUFFICIENT_EVIDENCE"

    claim_emb = embedder.encode(claim, convert_to_tensor=True)
    evidence_emb = embedder.encode(evidence, convert_to_tensor=True)

    scores = util.cos_sim(claim_emb, evidence_emb)
    max_score = scores.max().item()

    if max_score > 0.6:
        return "SUPPORTED"
    elif max_score < 0.2:
        return "CONTRADICTED"
    else:
        return "INSUFFICIENT_EVIDENCE"
