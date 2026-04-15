import time
from google import genai
from app.config import GEMINI_API_KEY, MODEL_NAME

client = genai.Client(api_key=GEMINI_API_KEY)

def generate(prompt,retries=3):
    for i in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"[LLM ERROR] Attempt {i+1}: {e}")
            time.sleep(2)
            
    return "LLM failed after retries"