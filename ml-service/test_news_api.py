import os
import requests
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
print(f"Testing NewsAPI with KEY: {NEWS_API_KEY}")

query = "technology"

# Testing newsapi.org (as used in evidence_service.py)
print("\n--- Testing NewsAPI.org ---")
res = requests.get(
    "https://newsapi.org/v2/everything",
    params={"q": query, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 1},
    timeout=5
)
print("Status:", res.status_code)
try:
    print(res.json())
except:
    print(res.text)

# Testing newsdata.io (since key starts with 'pub_')
print("\n--- Testing NewsData.io (Fallback check) ---")
res_data = requests.get(
    "https://newsdata.io/api/1/news",
    params={"q": query, "apikey": NEWS_API_KEY},
    timeout=5
)
print("Status:", res_data.status_code)
try:
    print(res_data.json())
except:
    print(res_data.text)
