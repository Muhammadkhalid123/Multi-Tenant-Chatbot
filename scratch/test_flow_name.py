import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_chat_flow():
    # We will use a unique session ID
    session_id = "test_session_456"
    
    # Clean the session first
    requests.post(f"{BASE_URL}/clear_session", json={"session_id": session_id})
    print("Session cleared.")
    
    # Message 1
    m1 = "how could you help me"
    print(f"User: {m1}")
    r1 = requests.post(f"{BASE_URL}/ask", json={"question": m1, "session_id": session_id})
    res1 = r1.json()
    print(f"Bot: {res1.get('answer')}\n")
    
    # Message 2
    m2 = "My name is Alex"
    print(f"User: {m2}")
    r2 = requests.post(f"{BASE_URL}/ask", json={"question": m2, "session_id": session_id})
    res2 = r2.json()
    print(f"Bot: {res2.get('answer')}\n")
    
    # Message 3 (Verify name context is preserved)
    m3 = "What services do you offer?"
    print(f"User: {m3}")
    r3 = requests.post(f"{BASE_URL}/ask", json={"question": m3, "session_id": session_id})
    res3 = r3.json()
    print(f"Bot: {res3.get('answer')}\n")

if __name__ == "__main__":
    test_chat_flow()
