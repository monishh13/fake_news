import torch
from sentence_transformers import SentenceTransformer, util
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

try:
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print("Warning: unable to load SentenceTransformer for evidence service", e)
    embedder = None

import wikipedia
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_FACT_CHECK_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def extract_keywords_entities(text: str) -> list[str]:
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents]
    keywords = [chunk.text for chunk in doc.noun_chunks]
    return list(set(entities + keywords))

def search_trusted_sources(claim: str) -> list[str]:
    """Retrieve evidence snippets dynamically using the Wikipedia API based on claim keywords."""
    if not embedder:
        return []
    
    # 1. Extract keywords to form a search query
    keywords = extract_keywords_entities(claim)
    if not keywords:
        # Fallback if no specific entities/nouns found
        keywords = [token.text for token in nlp(claim) if not token.is_stop and token.is_alpha][:5]
        if not keywords:
            keywords = claim.split()[:5]
        
    query = " ".join(keywords[:3]) # Use top 3 strongest keywords for broader search
    
    snippets = []
    
    # --- 1. Google Fact Check Tools API ---
    if GOOGLE_FACT_CHECK_API_KEY:
        try:
            res = requests.get(
                "https://factchecktools.googleapis.com/v1alpha1/claims:search",
                params={"query": query, "key": GOOGLE_FACT_CHECK_API_KEY},
                timeout=5
            )
            if res.status_code == 200:
                data = res.json()
                if 'claims' in data:
                    for c in data['claims'][:2]:
                        if 'claimReview' in c and c['claimReview']:
                            review = c['claimReview'][0]
                            publisher = review.get('publisher', {}).get('name', 'Fact-checker')
                            rating = review.get('textualRating', 'Unknown')
                            snippets.append(f"[Google Fact Check] {publisher} rating: {rating}. Original claim: {c.get('text', '')}")
            else:
                print(f"Google Fact Check API Error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"Google Fact Check API error: {e}")

    # --- 2. News API (NewsAPI.org or NewsData.io) ---
    if NEWS_API_KEY:
        try:
            if NEWS_API_KEY.startswith("pub_"):
                # NewsData.io
                res = requests.get(
                    "https://newsdata.io/api/1/news",
                    params={"q": query, "apikey": NEWS_API_KEY, "language": "en"},
                    timeout=5
                )
                if res.status_code == 200:
                    data = res.json()
                    if 'results' in data:
                        for art in data['results'][:3]:
                            desc = art.get('description') or art.get('content')
                            if desc and len(desc) > 20:
                                source = art.get('source_id', 'News')
                                snippets.append(f"[NewsData - {source}] {desc[:300].strip()}")
                else:
                    print(f"NewsData.io Error ({res.status_code}): {res.text}")
            else:
                # NewsAPI.org
                res = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": query, "apiKey": NEWS_API_KEY, "language": "en", "sortBy": "relevancy", "pageSize": 3},
                    timeout=5
                )
                if res.status_code == 200:
                    data = res.json()
                    if 'articles' in data:
                        for art in data['articles']:
                            desc = art.get('description')
                            if desc and len(desc) > 20:
                                snippets.append(f"[NewsAPI - {art.get('source', {}).get('name', 'News')}] {desc.strip()}")
                else:
                    print(f"NewsAPI Error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"News API error: {e}")

    try:
        # --- 3. Wikipedia Fallback / Semantic Search ---
        search_results = wikipedia.search(query, results=2)
        
        wiki_snippets = []
        for title in search_results:
            try:
                # 3. Fetch summary of the top matching articles (limit sentences for speed)
                page_summary = wikipedia.summary(title, sentences=3, auto_suggest=False)
                
                # Split summary into individual sentences to act as separate evidence snippets
                sentences = [s.text.strip() for s in nlp(page_summary).sents if len(s.text.strip()) > 20]
                wiki_snippets.extend([f"[Wikipedia] {s}" for s in sentences])
            except wikipedia.exceptions.DisambiguationError as e:
                # If ambiguous, just grab the first option's summary instead of crashing
                try:
                    page_summary = wikipedia.summary(e.options[0], sentences=2, auto_suggest=False)
                    sentences = [s.text.strip() for s in nlp(page_summary).sents if len(s.text.strip()) > 20]
                    wiki_snippets.extend([f"[Wikipedia] {s}" for s in sentences])
                except Exception:
                    pass 
            except Exception:
                pass
                
        # 4. Filter ONLY Wikipedia sentences using Semantic Similarity
        filtered_wiki_snippets = []
        if wiki_snippets:
            claim_emb = embedder.encode(claim, convert_to_tensor=True)
            evidence_embs = embedder.encode(wiki_snippets, convert_to_tensor=True)
            
            cosine_scores = util.cos_sim(claim_emb, evidence_embs)[0]
            
            # Keep top 3 most semantically relevant sentences from the Wikipedia summaries
            top_k = min(3, len(wiki_snippets))
            top_results = torch.topk(cosine_scores, k=top_k)
            
            for score, idx in zip(top_results[0], top_results[1]):
                if score.item() > 0.10: 
                    filtered_wiki_snippets.append(wiki_snippets[idx])
                    
        return snippets + filtered_wiki_snippets
        
    except Exception as e:
        print(f"Wikipedia search failed: {e}")
        return snippets

def compute_evidence_similarity(claim: str, evidence: list[str]) -> str:
    """Determine whether the claim is SUPPORTED, CONTRADICTED, or INSUFFICIENT_EVIDENCE."""
    if not evidence or not embedder:
        return "INSUFFICIENT_EVIDENCE"
        
    claim_emb = embedder.encode(claim, convert_to_tensor=True)
    evidence_emb = embedder.encode(evidence, convert_to_tensor=True)
    
    scores = util.cos_sim(claim_emb, evidence_emb)
    max_score = scores.max().item()
    
    # Ideally an NLI cross-encoder should be used. Using threshold logic on similarity as a proxy.
    if max_score > 0.6:
        return "SUPPORTED"
    elif max_score < 0.2:
        return "CONTRADICTED"
    else:
        return "INSUFFICIENT_EVIDENCE"
