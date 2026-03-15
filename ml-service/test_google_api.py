import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_FACT_CHECK_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
print("KEY:", GOOGLE_FACT_CHECK_API_KEY)

query = "Netanyahu coffee video"

res = requests.get(
    "https://factchecktools.googleapis.com/v1alpha1/claims:search",
    params={"query": query, "key": GOOGLE_FACT_CHECK_API_KEY},
    timeout=5
)
print("Status:", res.status_code)
if res.status_code == 200:
    print(res.json())
else:
    print(res.text)
