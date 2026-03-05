import traceback
try:
    from services.evidence_service import search_trusted_sources
    
    print("Testing Claim 1: 'Vaccines cause autism'")
    ev = search_trusted_sources("Vaccines cause autism")
    print(ev)
    
    print("\nTesting Claim 2: 'The earth is flat'")
    ev2 = search_trusted_sources("The earth is flat")
    print(ev2)
    
except Exception as e:
    traceback.print_exc()
