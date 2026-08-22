import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()
session_id = "test_khalid_session_123"
bot_id = "indie_global"

# Step 1: hi there
res1 = client.post("/ask", json={"question": "hi there", "session_id": session_id, "bot_id": bot_id})
print("\n--- Step 1: 'hi there' ---", flush=True)
data1 = res1.get_json()
print("Status:", res1.status_code, flush=True)
print("Answer:", data1.get("answer"), flush=True)

# Step 2: my name is khalid
res2 = client.post("/ask", json={"question": "my name is khalid", "session_id": session_id, "bot_id": bot_id})
print("\n--- Step 2: 'my name is khalid' ---", flush=True)
data2 = res2.get_json()
print("Status:", res2.status_code, flush=True)
print("Answer:", data2.get("answer"), flush=True)

# Step 3: i want the marketing
res3 = client.post("/ask", json={"question": "i want the marketing", "session_id": session_id, "bot_id": bot_id})
print("\n--- Step 3: 'i want the marketing' ---", flush=True)
data3 = res3.get_json()
print("Status:", res3.status_code, flush=True)
print("Answer:", data3.get("answer"), flush=True)
