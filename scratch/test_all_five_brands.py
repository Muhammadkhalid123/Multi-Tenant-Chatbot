import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()

brands_to_test = [
    ("indie_global", "Tell me about your global publishing and retail distribution."),
    ("kandle_direct", "How do you help authors publish on Amazon KDP?"),
    ("self_publishing", "What editorial and cover design services do you offer?"),
    ("influitivezone", "Can you build a custom website and help with SEO?"),
    ("tecwrites", "Can you help with technical API documentation and web dev?")
]

print("\n--- Testing Live /ask for All 5 Brands ---", flush=True)

for bot_id, question in brands_to_test:
    session_id = f"test_{bot_id}_session"
    res = client.post("/ask", json={
        "bot_id": bot_id,
        "question": question,
        "session_id": session_id
    })
    
    data = res.get_json() or {}
    print(f"\n[{bot_id}] Status: {res.status_code}", flush=True)
    print(f"Reply: {data.get('answer', data.get('reply'))}", flush=True)
    assert res.status_code == 200, f"Failed on {bot_id}"

print("\n[SUCCESS] All 5 brands tested successfully!", flush=True)
