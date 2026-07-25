import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_multi_tenant():
    session_id = "test_session_multi_999"
    
    print("--- 1. Testing Config Endpoints ---")
    
    # Test brand 1 config
    r_sp = requests.get(f"{BASE_URL}/config/self_publishing")
    print(f"Self Publishing Config Status: {r_sp.status_code}")
    print(f"Self Publishing Brand Name: {r_sp.json().get('brand_name')}")
    print(f"Self Publishing Primary Color: {r_sp.json().get('primary_color')}\n")
    
    # Test brand 2 config
    r_tb = requests.get(f"{BASE_URL}/config/test_brand")
    print(f"Test Brand Config Status: {r_tb.status_code}")
    print(f"Test Brand Name: {r_tb.json().get('brand_name')}")
    print(f"Test Brand Primary Color: {r_tb.json().get('primary_color')}\n")
    
    print("--- 2. Testing Chat Endpoint (test_brand) ---")
    
    # Clear session for test_brand
    requests.post(f"{BASE_URL}/clear_session", json={"session_id": session_id, "bot_id": "test_brand"})
    
    # Ask test_brand a question
    q1 = "what services do you guys offer?"
    print(f"User asking [test_brand]: '{q1}'")
    r1 = requests.post(f"{BASE_URL}/ask", json={
        "question": q1,
        "session_id": session_id,
        "bot_id": "test_brand"
    })
    res1 = r1.json()
    print(f"Bot [test_brand] Answer:\n{res1.get('answer')}\n")
    
    print("--- 3. Testing Chat Endpoint (self_publishing) ---")
    
    # Clear session for self_publishing
    requests.post(f"{BASE_URL}/clear_session", json={"session_id": session_id, "bot_id": "self_publishing"})
    
    # Ask self_publishing a question
    q2 = "what editing services do you offer?"
    print(f"User asking [self_publishing]: '{q2}'")
    r2 = requests.post(f"{BASE_URL}/ask", json={
        "question": q2,
        "session_id": session_id,
        "bot_id": "self_publishing"
    })
    res2 = r2.json()
    print(f"Bot [self_publishing] Answer:\n{res2.get('answer')}\n")

if __name__ == "__main__":
    test_multi_tenant()
