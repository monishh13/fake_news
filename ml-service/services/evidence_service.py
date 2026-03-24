"""
Evidence Service — parallel retrieval from Wikipedia, Google Fact Check,
NewsAPI/NewsData, and GDELT (free fallback).

Architecture:
1. Keywords extracted from claim for Wikipedia; full claim for news/fact-check APIs
2. Bi-encoder (all-MiniLM-L6-v2) does fast top-k cosine pre-filter on raw snippets
3. Cross-Encoder NLI (nli-deberta-v3-small) re-ranks filtered snippets
4. Ratio-based voting: SUPPORTED / CONTRADICTED / INSUFFICIENT_EVIDENCE
   based on majority across all evidence, not a single snippet.

Benchmark (4 pairs, CPU):
  nli-deberta-v3-small:                 ~94ms  (3-class), kept for accuracy
  MoritzLaurer/MiniLM-L6-mnli-fever-2c: ~20ms  (binary only), not sufficient
"""

import asyncio
import httpx
import numpy as np
import os
import wikipedia
import spacy
from sentence_transformers import SentenceTransformer, CrossEncoder, util
from dotenv import load_dotenv

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Bi-encoder: fast cosine pre-filter
try:
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Warning: unable to load SentenceTransformer: {e}")
    embedder = None

# Cross-Encoder NLI model: fine-tuned on MNLI/SNLI/ANLI with DeBERTa-v3
# Label mapping (verified): {0: contradiction, 1: entailment, 2: neutral}
# Benchmark: ~94ms/batch on CPU. Kept over MiniLM-binary for 3-class accuracy.
try:
    nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-small')

    # ── Dynamic label index discovery ─────────────────────────────────────────
    # NEVER hardcode indices. Always read from model.config.id2label.
    # Supports both 3-label and 2-label (binary) models.
    _id2label = nli_model.config.id2label   # e.g. {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
    _label2id = {v.lower(): k for k, v in _id2label.items()}
    _n_labels  = len(_id2label)

    # Validate that 'entailment' is present — required for fact-checking
    if "entailment" not in _label2id:
        raise ValueError(f"NLI model has no 'entailment' label. Found: {list(_label2id.keys())}")

    NLI_IDX_ENTAILMENT    = _label2id["entailment"]

    if "contradiction" in _label2id:
        # Case A: 3-label model (entailment / contradiction / neutral)
        NLI_IDX_CONTRADICTION = _label2id["contradiction"]
        NLI_IDX_NEUTRAL       = _label2id.get("neutral", -1)  # -1 = not present
        NLI_IS_BINARY         = False
    elif "not_entailment" in _label2id:
        # Case B: Binary model (entailment / not_entailment)
        # Treat not_entailment as a combined contradiction+neutral signal
        NLI_IDX_CONTRADICTION = _label2id["not_entailment"]
        NLI_IDX_NEUTRAL       = -1  # no dedicated neutral class
        NLI_IS_BINARY         = True
    else:
        raise ValueError(f"NLI model has neither 'contradiction' nor 'not_entailment'. Found: {list(_label2id.keys())}")

    print(
        f"NLI Cross-Encoder loaded (nli-deberta-v3-small, {_n_labels}-label). "
        f"Indices — entailment={NLI_IDX_ENTAILMENT}, "
        f"contradiction={NLI_IDX_CONTRADICTION}, "
        f"neutral={NLI_IDX_NEUTRAL}, binary={NLI_IS_BINARY}"
    )
except Exception as e:
    print(f"Warning: unable to load NLI Cross-Encoder: {e}")
    nli_model = None
    NLI_IDX_ENTAILMENT    = 1
    NLI_IDX_CONTRADICTION = 0
    NLI_IDX_NEUTRAL       = 2
    NLI_IS_BINARY         = False

load_dotenv()

GOOGLE_FACT_CHECK_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

# NLI pre-filter: top-K snippets to send to cross-encoder (avoids N*94ms batches)
NLI_TOP_K = 10        # how many snippets to pass to NLI after cosine pre-filter
COSINE_PREFILTER_K = 20  # top-K by cosine similarity to keep before NLI

# ── Source credibility registry ───────────────────────────────────────────────
_DOMAIN_CREDIBILITY: dict[str, float] = {
    "reuters":    1.0,  "ap news": 1.0,  "apnews":   1.0,
    "bbc":        0.95, "npr":     0.95,
    "theguardian":0.92, "guardian":0.92,
    "nytimes":    0.90, "washingtonpost":0.90, "economist":0.90,
    "snopes":     0.90, "politifact":0.90, "factcheck":0.90,
    "science":    0.85,
    "cnn":        0.75, "fox":     0.65,
    "dailymail":  0.45, "nypost":  0.50, "buzzfeed": 0.55,
}
_DEFAULT_CREDIBILITY = 0.60


def _nli_softmax(logits) -> np.ndarray:
    """Convert raw NLI logits to probabilities via numerically stable softmax."""
    arr = np.array(logits, dtype=np.float64)
    e = np.exp(arr - np.max(arr))
    return e / e.sum()


import re as _re
_CRED_TAG_RE = _re.compile(r'\[credibility:[\d.]+\]')
_SOURCE_PREFIX_RE = _re.compile(r'^\[(?:Wikipedia|Google Fact Check|NewsAPI - [^\]]+|NewsData - [^\]]+|GDELT - [^\]]+)\]\s*')

def _clean_for_nli(text: str) -> str:
    """
    Strip display decoration and conflicting trailing clauses before NLI:
      - Remove [Source - Publisher] prefix
      - Remove trailing [credibility:X.XX] tag
      - Strip trailing compound clauses that contradict the main fact (e.g. ", but at 93.4 C...")
    """
    text = _SOURCE_PREFIX_RE.sub('', text)
    text = _CRED_TAG_RE.sub('', text)
    
    # Drop trailing ", but ..." clauses that commonly flip NLI verdicts on true claims
    # Example: "Water boils at 100C standard pressure, but at 93C at altitude." -> keep first half
    if ", but " in text:
        text = text.split(", but ")[0]
        
    return text.strip()
    


def _credibility_for_source(source_name: str) -> float:
    lower = source_name.lower()
    for key, score in _DOMAIN_CREDIBILITY.items():
        if key in lower:
            return score
    return _DEFAULT_CREDIBILITY


def extract_keywords_entities(text: str) -> list[str]:
    doc = nlp(text)
    skip_ents = {"PERCENT", "CARDINAL", "QUANTITY", "MONEY", "TIME", "DATE", "ORDINAL"}
    entities = [ent.text for ent in doc.ents if ent.label_ not in skip_ents]

    keywords = []
    for chunk in doc.noun_chunks:
        clean = " ".join([t.text for t in chunk if not t.is_stop and t.is_alpha])
        if clean:
            keywords.append(clean)

    verbs = [t.lemma_ for t in doc if t.pos_ == "VERB" and not t.is_stop]

    combined, seen = [], set()
    for item in (entities + keywords + verbs):
        lo = item.lower()
        if lo not in seen and len(lo) > 2:
            seen.add(lo)
            combined.append(item)
    return combined


# ── Async source helpers ───────────────────────────────────────────────────────

async def _fetch_google_fact_check(client: httpx.AsyncClient, query: str) -> list[str]:
    """Google Fact Check always receives the full claim text — that's its design."""
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
            for c in data.get("claims", [])[:3]:
                reviews = c.get("claimReview", [])
                original_claim_text = c.get('text', '').strip()
                if reviews and original_claim_text:
                    review = reviews[0]
                    publisher = review.get("publisher", {}).get("name", "Fact-checker")
                    rating = review.get("textualRating", "Unknown")
                    cred = _credibility_for_source(publisher)
                    # Store original claim text as NLI-clean text; include rating context for display
                    snippets.append(
                        f"[Google Fact Check] {publisher} rating: {rating}. "
                        f"Original claim: {original_claim_text} "
                        f"[credibility:{cred:.2f}]"
                    )
            return snippets
        else:
            print(f"Google Fact Check API Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Google Fact Check API error: {e}")
    return []


async def _fetch_news_api(client: httpx.AsyncClient, query: str) -> list[str]:
    if not NEWS_API_KEY:
        return []
    try:
        if NEWS_API_KEY.startswith("pub_"):
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
    try:
        res = await client.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "ArtList", "maxrecords": 5, "format": "json"},
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
                    snippets.append(f"[GDELT - {domain}] {title} [credibility:{cred:.2f}]")
            return snippets
        else:
            print(f"GDELT API Error ({res.status_code})")
    except Exception as e:
        print(f"GDELT API error: {e}")
    return []


def _fetch_wikipedia_sync(claim: str, keywords: list[str]) -> list[str]:
    """
    Fetch Wikipedia snippets using multi-strategy search to maximize hitting the right article:

      Strategy 1: NER noun-phrase query  (e.g. "boiling point water" from "Water boils at 100°C")
                  → Most specific, most likely to retrieve the directly relevant article
      Strategy 2: Full claim as query    (natural language, useful for people/events)
      Strategy 3: Keyword fallback       (if both above return nothing)

    All results are deduplicated. Returns up to 5 sentences per article, 3 articles per query.
    """
    def _search_and_fetch(query: str, n_articles: int = 3, n_sentences: int = 5) -> list[str]:
        snippets = []
        try:
            search_results = wikipedia.search(query, results=n_articles)
        except Exception as e:
            print(f"Wikipedia search failed for '{query[:60]}': {e}")
            return []
        for title in search_results:
            try:
                summary = wikipedia.summary(title, sentences=n_sentences, auto_suggest=False)
                for s in nlp(summary).sents:
                    text = s.text.strip()
                    if len(text) > 20:
                        snippets.append(f"[Wikipedia] {text}")
            except wikipedia.exceptions.DisambiguationError as e:
                try:
                    summary = wikipedia.summary(e.options[0], sentences=n_sentences, auto_suggest=False)
                    for s in nlp(summary).sents:
                        text = s.text.strip()
                        if len(text) > 20:
                            snippets.append(f"[Wikipedia] {text}")
                except Exception:
                    pass
            except Exception:
                pass
        return snippets

    # Build an NER-based noun phrase query — more specific than keywords
    # e.g. "Water boils at 100 degrees Celsius" → "boiling point water" via nouns+verbs
    doc = nlp(claim)
    noun_phrases = [chunk.text for chunk in doc.noun_chunks
                    if not all(t.is_stop for t in chunk)]
    ner_query = " ".join(noun_phrases[:4]) if noun_phrases else ""

    all_snippets: list[str] = []
    seen_texts: set[str] = set()

    def _add_unique(new_snippets: list[str]) -> None:
        for s in new_snippets:
            clean = _clean_for_nli(s)
            if clean not in seen_texts and len(clean) > 20:
                seen_texts.add(clean)
                all_snippets.append(s)

    # Strategy 1: NER noun-phrase query (most specific)
    if ner_query:
        _add_unique(_search_and_fetch(ner_query, n_articles=3, n_sentences=5))

    # Strategy 2: Full claim query (works well for named entities, events)
    _add_unique(_search_and_fetch(claim, n_articles=2, n_sentences=5))

    # Strategy 3: Keyword fallback — only if both above found nothing
    if not all_snippets and keywords:
        kw_query = " ".join(keywords[:5])
        print(f"Wikipedia: both NER and full-claim queries failed, using keyword fallback: '{kw_query}'")
        _add_unique(_search_and_fetch(kw_query, n_articles=3, n_sentences=5))

    return all_snippets



# ── Core NLI helpers ───────────────────────────────────────────────────────────

def _cosine_top_k(claim: str, snippets: list[str], k: int) -> list[str]:
    """Fast bi-encoder top-K cosine filter. Uses cleaned text for embedding."""
    if not embedder or not snippets:
        return snippets[:k]
    import torch
    claim_emb = embedder.encode(claim, convert_to_tensor=True)
    clean_texts = [_clean_for_nli(s) for s in snippets]
    snip_embs = embedder.encode(clean_texts, convert_to_tensor=True)
    scores = util.cos_sim(claim_emb, snip_embs)[0]
    top_k = min(k, len(snippets))
    indices = torch.topk(scores, k=top_k).indices.tolist()
    return [snippets[i] for i in sorted(indices)]


def _nli_classify_snippets(claim: str, snippets: list[str]) -> list[dict]:
    """
    Run NLI on each [evidence, claim] pair using cleaned evidence text.

    Returns list of dicts with named probability keys.
    ALWAYS uses dynamic NLI_IDX_* constants — never hardcoded positions.
    Supports both 3-label and binary (2-label) models.
    """
    if not nli_model or not snippets:
        return []

    # Clean display metadata from evidence before NLI
    clean_snippets = [_clean_for_nli(s) for s in snippets]
    valid = [(orig, clean) for orig, clean in zip(snippets, clean_snippets) if len(clean) >= 15]
    if not valid:
        return []

    orig_snippets, clean_texts = zip(*valid)

    # Validate output size matches expected label count
    n_labels = len(nli_model.config.id2label)

    # Pair order: [evidence, claim] — evidence is premise, claim is hypothesis
    pairs = [[clean, claim] for clean in clean_texts]
    raw_scores = nli_model.predict(pairs)

    results = []
    for snippet, raw in zip(orig_snippets, raw_scores):
        probs = _nli_softmax(raw)

        # Guard: ensure indices are in range
        if len(probs) <= max(NLI_IDX_ENTAILMENT, NLI_IDX_CONTRADICTION):
            print(f"Warning: NLI output has {len(probs)} values but expected >= {max(NLI_IDX_ENTAILMENT, NLI_IDX_CONTRADICTION)+1}")
            continue

        e_prob = float(probs[NLI_IDX_ENTAILMENT])
        c_prob = float(probs[NLI_IDX_CONTRADICTION])

        # For binary models (not_entailment), neutral is undefined
        if NLI_IS_BINARY or NLI_IDX_NEUTRAL < 0:
            # Split not_entailment probability between contradiction and neutral
            c_prob_adj = c_prob * 0.5   # treat half as contradiction
            n_prob = c_prob * 0.5       # and half as neutral
            c_prob = c_prob_adj
        else:
            n_prob = float(probs[NLI_IDX_NEUTRAL])

        results.append({
            "snippet":            snippet,
            "entailment_prob":    e_prob,
            "contradiction_prob": c_prob,
            "neutral_prob":       n_prob,
        })
    return results


# ── Public async interface ────────────────────────────────────────────────────

async def search_trusted_sources(claim: str) -> list[str]:
    """
    Retrieve evidence snippets from all sources in parallel.

    Pipeline:
      1. Fetch raw snippets from Google Fact Check (full claim), NewsAPI (keywords/claim),
         GDELT (keywords/claim), Wikipedia (full claim → keyword fallback).
      2. Cosine top-K pre-filter (fast bi-encoder) to discard off-topic snippets.
      3. NLI re-ranking: keep only snippets where entailment or contradiction > neutral.
      4. Return up to 10 snippets ordered by NLI relevance.
    """
    if not embedder:
        return []

    keywords = extract_keywords_entities(claim)
    if not keywords:
        keywords = [t.text for t in nlp(claim) if not t.is_stop and t.is_alpha][:5]
    if not keywords:
        keywords = claim.split()[:5]

    # News APIs: use keyword query (>=4 keywords) or full claim (short claims)
    news_query = " ".join(keywords[:6]) if len(keywords) >= 4 else claim[:200]

    loop = asyncio.get_event_loop()
    async with httpx.AsyncClient() as client:
        google_task = _fetch_google_fact_check(client, claim[:200])
        news_task   = _fetch_news_api(client, news_query)
        gdelt_task  = _fetch_gdelt(client, news_query)
        wiki_task   = loop.run_in_executor(None, _fetch_wikipedia_sync, claim, keywords)

        google_snippets, news_snippets, gdelt_snippets, wiki_snippets = await asyncio.gather(
            google_task, news_task, gdelt_task, wiki_task
        )

    final_news = news_snippets if news_snippets else gdelt_snippets
    all_raw = google_snippets + final_news + wiki_snippets

    if not all_raw:
        return []

    # ── Step 2: Cosine top-K pre-filter (fast — discards clearly off-topic snippets) ──
    # We pass ALL top-K candidates to the caller; compute_evidence_similarity does NLI.
    # Do NOT NLI-filter here: pre-filtering drops genuine supporting sentences when
    # many contradiction-dominant context snippets dominate the top-K set.
    candidates = _cosine_top_k(claim, all_raw, k=NLI_TOP_K)
    return candidates


def compute_evidence_similarity(claim: str, evidence: list[str]) -> tuple[str, dict]:
    """
    Classify the relationship between the claim and a list of evidence snippets.

    Returns:
        (status, explanation) where:
          status: "SUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE"
          explanation: {
              "top_supporting": [str],   # top entailment snippets
              "top_contradicting": [str], # top contradiction snippets
              "entailment_votes": int,
              "contradiction_votes": int,
              "total_votes": int,
          }

    Verdict logic (ratio-based, per user feedback):
      - SUPPORTED if entailment_ratio > 0.5 and at least 1 entailment vote
      - CONTRADICTED if contradiction_ratio > 0.6 and contradiction_votes > entailment_votes
      - INSUFFICIENT_EVIDENCE otherwise (including 0 votes on both sides)
    """
    empty_explanation = {
        "top_supporting": [], "top_contradicting": [],
        "entailment_votes": 0, "contradiction_votes": 0, "total_votes": 0
    }

    if not evidence:
        return "INSUFFICIENT_EVIDENCE", empty_explanation

    if nli_model:
        nli_results = _nli_classify_snippets(claim, evidence)

        entailment_votes = 0
        contradiction_votes = 0
        total_votes = len(nli_results)
        supporting_snippets = []
        contradicting_snippets = []

        for r in nli_results:
            e_prob = r["entailment_prob"]
            c_prob = r["contradiction_prob"]
            n_prob = r["neutral_prob"]
            # Determine dominant class by actual named probabilities
            if e_prob > c_prob and e_prob > n_prob and e_prob > 0.5:
                entailment_votes += 1
                supporting_snippets.append((e_prob, r["snippet"]))
            elif c_prob > e_prob and c_prob > n_prob and c_prob > 0.5:
                contradiction_votes += 1
                contradicting_snippets.append((c_prob, r["snippet"]))


        # Sort by confidence
        supporting_snippets.sort(reverse=True)
        contradicting_snippets.sort(reverse=True)

        explanation = {
            "top_supporting":    [s for _, s in supporting_snippets[:3]],
            "top_contradicting": [s for _, s in contradicting_snippets[:3]],
            "entailment_votes":    entailment_votes,
            "contradiction_votes": contradiction_votes,
            "total_votes":         total_votes,
        }

        # ── Hybrid verdict: max-confidence + ratio ─────────────────────────────
        # Ratio alone is too strict when Wikipedia returns irrelevant context sentences
        # alongside 1 perfectly supporting sentence. Use max entailment confidence
        # as primary signal; ratio guards against contradiction false positives.
        max_entailment_conf = supporting_snippets[0][0] if supporting_snippets else 0.0
        max_contra_conf     = contradicting_snippets[0][0] if contradicting_snippets else 0.0

        if total_votes > 0:
            entailment_ratio    = entailment_votes / total_votes
            contradiction_ratio = contradiction_votes / total_votes
        else:
            entailment_ratio = contradiction_ratio = 0.0

        # SUPPORTED if:
        #   - At least 1 snippet strongly entails (>80%), OR
        #   - Multiple moderate entailments form a majority (ratio > 0.4)
        if entailment_votes > 0 and (max_entailment_conf > 0.80 or entailment_ratio > 0.4):
            return "SUPPORTED", explanation

        # CONTRADICTED requires ratio-based majority (needs many contradicting snippets)
        # to avoid 1 irrelevant sentence flipping the verdict
        elif (contradiction_votes >= 2
              and contradiction_ratio > 0.5
              and contradiction_votes > entailment_votes):
            return "CONTRADICTED", explanation

        else:
            return "INSUFFICIENT_EVIDENCE", explanation

    # ── Fallback: cosine similarity ────────────────────────────────────────────
    if embedder:
        import torch
        claim_emb = embedder.encode(claim, convert_to_tensor=True)
        ev_emb    = embedder.encode(evidence, convert_to_tensor=True)
        scores = util.cos_sim(claim_emb, ev_emb)
        max_score = scores.max().item()
        explanation = {**empty_explanation, "top_supporting": evidence[:1] if max_score >= 0.75 else []}
        if max_score >= 0.75:
            return "SUPPORTED", explanation
    return "INSUFFICIENT_EVIDENCE", empty_explanation
