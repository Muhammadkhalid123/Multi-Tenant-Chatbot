import os
os.environ["GROQ_API_KEY"] = "dummy_key"
os.environ["MONGO_URI"] = "mongodb://localhost:27017/chatbot?serverSelectionTimeoutMS=500"

import sys
sys.path.insert(0, ".")
import app

print("Successfully loaded app.py!")
print(f"Total routes registered: {len(list(app.app.url_map.iter_rules()))}")
for r in app.app.url_map.iter_rules():
    if "admin" in r.rule or "tenant" in r.rule or r.rule == "/":
        print(f"  {r.rule:30s} -> {r.endpoint}")
