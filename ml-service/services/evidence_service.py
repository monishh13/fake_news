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


def extract_keywords_entities(text: str) -> list[str]:
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents]
    keywords = [chunk.text for chunk in doc.noun_chunks]
    return list(set(entities + keywords))


# ── Async helpers for each source ──────────────────────────────────────────────

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
                    snippets.append(
                        f"[Google Fact Check] {publisher} rating: {rating}. "
                        f"Original claim: {c.get('text', '')}"
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
                        snippets.append(f"[NewsData - {source}] {desc[:300].strip()}")
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
                        snippets.append(
                            f"[NewsAPI - {art.get('source', {}).get('name', 'News')}] {desc.strip()}"
                        )
                return snippets
            else:
                print(f"NewsAPI Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"News API error: {e}")
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


# ── Public async interface ──────────────────────────────────────────────────────

async def search_trusted_sources(claim: str) -> list[str]:
    """
    Retrieve evidence snippets from all three sources **in parallel**.
    Total latency ≈ max(individual latencies) instead of their sum.
    """
    if not embedder:
        return []

    keywords = extract_keywords_entities(claim)
    if not keywords:
        keywords = [t.text for t in nlp(claim) if not t.is_stop and t.is_alpha][:5]
    if not keywords:
        keywords = claim.split()[:5]

    query = " ".join(keywords[:3])

    # Fire all three sources concurrently
    loop = asyncio.get_event_loop()
    async with httpx.AsyncClient() as client:
        google_task = _fetch_google_fact_check(client, query)
        news_task = _fetch_news_api(client, query)
        wiki_task = loop.run_in_executor(None, _fetch_wikipedia_sync, query)

        google_snippets, news_snippets, wiki_snippets_raw = await asyncio.gather(
            google_task, news_task, wiki_task
        )

    # Semantic filter on Wikipedia results only
    filtered_wiki = []
    if wiki_snippets_raw and embedder:
        claim_emb = embedder.encode(claim, convert_to_tensor=True)
        evidence_embs = embedder.encode(wiki_snippets_raw, convert_to_tensor=True)
        cosine_scores = util.cos_sim(claim_emb, evidence_embs)[0]
        top_k = min(3, len(wiki_snippets_raw))
        top_results = torch.topk(cosine_scores, k=top_k)
        for score, idx in zip(top_results[0], top_results[1]):
            if score.item() > 0.10:
                filtered_wiki.append(wiki_snippets_raw[idx])

    return google_snippets + news_snippets + filtered_wiki


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
