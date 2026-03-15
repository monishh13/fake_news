import requests
from bs4 import BeautifulSoup

def extract_article_from_url(url: str) -> tuple[str, str]:
    """
    Downloads the HTML of the given URL and parses it using BeautifulSoup.
    Returns a tuple of (title, text).
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Try to get the title
        title = ''
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            
        # Try to extract the main content using common tags and classes
        # This is a naive approach; Trafilatura or newspaper3k are better, but BS4 is fine for Quick Wins.
        paragraphs = soup.find_all('p')
        text = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        return title, text
        
    except Exception as e:
        raise ValueError(f"Failed to extract URL content: {str(e)}")
