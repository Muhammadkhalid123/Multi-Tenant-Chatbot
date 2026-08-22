import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
res = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)
print("Groq Models Response Status:", res.status_code)
if res.ok:
    data = res.json()
    model_ids = [m["id"] for m in data.get("data", [])]
    print("Available Groq Models:")
    for m_id in model_ids:
        print(" -", m_id)
else:
    print("Error:", res.text)
