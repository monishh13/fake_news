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
        keywords = claim.split()[:5]
        
    query = " ".join(keywords[:3]) # Use top 3 strongest keywords for broader search
    
    snippets = []
    try:
        # 2. Search Wikipedia for matching pages
        search_results = wikipedia.search(query, results=2)
        
        for title in search_results:
            try:
                # 3. Fetch summary of the top matching articles (limit sentences for speed)
                page_summary = wikipedia.summary(title, sentences=3, auto_suggest=False)
                
                # Split summary into individual sentences to act as separate evidence snippets
                sentences = [s.text.strip() for s in nlp(page_summary).sents if len(s.text.strip()) > 20]
                snippets.extend(sentences)
            except wikipedia.exceptions.DisambiguationError as e:
                # If ambiguous, just grab the first option's summary instead of crashing
                try:
                    page_summary = wikipedia.summary(e.options[0], sentences=2, auto_suggest=False)
                    sentences = [s.text.strip() for s in nlp(page_summary).sents if len(s.text.strip()) > 20]
                    snippets.extend(sentences)
                except Exception:
                    pass 
            except Exception:
                pass
                
        # 4. Filter the extracted Wikipedia sentences using Semantic Similarity (SentenceTransformers)
        if not snippets:
            return []
            
        claim_emb = embedder.encode(claim, convert_to_tensor=True)
        evidence_embs = embedder.encode(snippets, convert_to_tensor=True)
        
        cosine_scores = util.cos_sim(claim_emb, evidence_embs)[0]
        
        # Keep top 3 most semantically relevant sentences from the Wikipedia summaries
        top_k = min(3, len(snippets))
        top_results = torch.topk(cosine_scores, k=top_k)
        
        filtered_snippets = []
        for score, idx in zip(top_results[0], top_results[1]):
            # Lower threshold slightly since live data is less perfectly aligned than mock data
            if score.item() > 0.15: 
                filtered_snippets.append(snippets[idx])
                
        return filtered_snippets
        
    except Exception as e:
        print(f"Wikipedia search failed: {e}")
        return []

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
