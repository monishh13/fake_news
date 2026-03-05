import traceback

try:
    from services.ml_service import analyze_claim, has_model
    print(f"Model loaded: {has_model}")
    
    score, explanation = analyze_claim("NASA confirms earth is flat")
    print(f"Score: {score}")
    print(f"Explanation: {explanation}")
    
    print("\n--- Testing with a true claim ---")
    score2, explanation2 = analyze_claim("Vaccines are safe and effective at preventing disease")
    print(f"Score: {score2}")
    print(f"Explanation: {explanation2}")
except Exception as e:
    traceback.print_exc()
