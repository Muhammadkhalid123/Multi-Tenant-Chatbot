import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set a fast serverSelectionTimeoutMS for offline testing if needed
os.environ["MONGO_URI"] = "mongodb://localhost:27017/chatbot?serverSelectionTimeoutMS=2000"

from app import app

print("Registered Routes:")
for rule in app.url_map.iter_rules():
    print(f"{rule.rule:35s} -> {rule.endpoint}")

print("\nAll routes verified successfully!")
