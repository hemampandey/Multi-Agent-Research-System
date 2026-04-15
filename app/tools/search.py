import requests
from app.config import TAVILY_API_KEY

def search_web(query):
    url = "https://api.tavily.com/search"
    
    data = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": 3
    }

    response = requests.post(url, json=data)
    return response.json()