import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import shap
import os
import hashlib
import json
from calibration import calibrate_score

CACHE_DIR = "cache/shap"
os.makedirs(CACHE_DIR, exist_ok=True)

model_path = "./model_weights/distilbert"
has_model = os.path.exists(model_path)

if has_model:
    from transformers import pipeline
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    # Using pipeline is the officially supported way to link HuggingFace with SHAP for text classification
    pred_pipe = pipeline("text-classification", model=model, tokenizer=tokenizer, return_all_scores=True)
    explainer = shap.Explainer(pred_pipe)
else:
    print("WARNING: DistilBERT model weights not found. Using mock prediction for development.")

def analyze_claim(claim_text: str) -> tuple[float, dict]:
    """
    Returns credibility score (0-1) and SHAP explanation dict {word: impact_score}
    """
    # 1. Check file cache
    claim_hash = hashlib.md5(claim_text.encode('utf-8')).hexdigest()
    cache_file = os.path.join(CACHE_DIR, f"{claim_hash}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data['score'], data['explanation']
        except Exception:
            pass # Ignore read errors and recompute
            
    # 2. Mock prediction fallback
    if not has_model:
        score = min(max(len(claim_text) / 200, 0.1), 0.9)
        mock_explain = {}
        words = claim_text.split()
        for i, word in enumerate(words[:10]):
            mock_explain[word] = np.random.uniform(-0.1, 0.2)
        return score, mock_explain

    inputs = tokenizer(claim_text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = torch.nn.functional.softmax(logits, dim=-1)
        raw_score = probabilities[0][1].item()
        # Feature 4: apply Platt scaling to correct overconfident softmax output
        credibility_score = calibrate_score(raw_score)
    # SHAP logic
    try:
        shap_values = explainer([claim_text])
        
        explanation = {}
        tokens = shap_values.data[0]
        values = shap_values.values[0]  # shape: (num_tokens, 2) for [LABEL_0, LABEL_1]
        
        # SHAP distributes attribution to the predicted class.
        # LABEL_0 = Fake, LABEL_1 = Real.
        # We want to show impact on credibility:
        #   - Positive value = word pushes towards "Real" (credible)
        #   - Negative value = word pushes towards "Fake" (not credible)
        # So we use: LABEL_1 values minus LABEL_0 values
        if len(values.shape) > 1 and values.shape[1] == 2:
            impacts = values[:, 1] - values[:, 0]
        else:
            impacts = values
            
        for token, impact in zip(tokens, impacts):
            tok_str = str(token).strip()
            if tok_str:
                explanation[tok_str] = round(float(impact), 6)
    except Exception as e:
        print(f"Error calculating SHAP: {e}")
        import traceback; traceback.print_exc()
        explanation = {"model_error": 0.0}

    # 3. Save to cache
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'score': credibility_score, 'explanation': explanation}, f)
    except Exception:
        pass

    return credibility_score, explanation
