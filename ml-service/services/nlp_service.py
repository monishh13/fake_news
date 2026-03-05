import spacy
import re

# Load small english model. Easiest to install: python -m spacy download en_core_web_sm
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def segment_claims(text: str) -> list[str]:
    """
    Extracts claims from text by splitting into sentences and filtering out short or non-declarative ones.
    """
    doc = nlp(text)
    claims = []
    
    for sent in doc.sents:
        # Basic filtering to remove very short sentences
        sent_str = sent.text.strip()
        if len(sent_str.split()) > 4 and re.search(r'[a-zA-Z]', sent_str):
            claims.append(sent_str)
            
    return claims
