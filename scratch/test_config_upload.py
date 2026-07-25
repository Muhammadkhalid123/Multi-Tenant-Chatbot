import requests

BASE_URL = "http://127.0.0.1:5000"

def test_dynamic_config_upload():
    bot_id = "dynamic_api_brand"
    session_id = "session_dynamic_upload_777"
    
    print("--- 1. Uploading Dynamic Configuration and Knowledge Base ---")
    payload = {
        "bot_id": bot_id,
        "brand_name": "Dynamic API Brand Inc",
        "welcome_message": "Welcome to Dynamic API Brand chatbot! We are here to help.",
        "primary_color": "#4f46e5",
        "primary_light_color": "#818cf8",
        "webhook_url": "https://dynamic-webhook.example.com",
        "admin_password": "api-admin-pass",
        "system_prompt": "You are a helpful assistant for Dynamic API Brand Inc.\n\nYou must respond ONLY in a valid JSON format with the following structure:\n{{\n  \"reply\": \"Your clear, concise, and helpful response text here\",\n  \"lead_required\": true/false,\n  \"extracted_name\": \"extracted user first name if they explicitly shared it or answered the name request in the current message, otherwise null\"\n}}\n\nDo not include any explanation, markdown wrappers (like ```json), or text outside of the JSON block.\n\nContext: {context}\n\nPrevious conversation: {history}\n\nQuestion: {question}\n\nJSON Response:",
        "knowledge_base": "# Dynamic API Brand Inc Services\n\nWe provide next-generation dynamic configurations, automated API management, serverless computing consulting, and secure database optimization. Our offices are remote-first."
    }
    
    r_upload = requests.post(f"{BASE_URL}/config/upload", json=payload)
    print(f"Upload Status Code: {r_upload.status_code}")
    print(f"Upload Response: {r_upload.json()}\n")
    
    assert r_upload.status_code == 200
    assert r_upload.json().get("success") is True
    
    print("--- 2. Testing Config Retrieval Endpoint ---")
    r_config = requests.get(f"{BASE_URL}/config/{bot_id}")
    print(f"Config Status Code: {r_config.status_code}")
    config_data = r_config.json()
    print(f"Config Brand Name: {config_data.get('brand_name')}")
    print(f"Config Primary Color: {config_data.get('primary_color')}")
    print(f"Config Welcome Message: {config_data.get('welcome_message')}\n")
    
    assert r_config.status_code == 200
    assert config_data.get("brand_name") == "Dynamic API Brand Inc"
    
    print("--- 3. Testing Dynamic Chat & RAG Retrieval ---")
    # Clear session first
    requests.post(f"{BASE_URL}/clear_session", json={"session_id": session_id, "bot_id": bot_id})
    
    # Ask a question related to their dynamic RAG documents
    q = "what services do you guys offer?"
    print(f"User asking [{bot_id}]: '{q}'")
    r_ask = requests.post(f"{BASE_URL}/ask", json={
        "question": q,
        "session_id": session_id,
        "bot_id": bot_id
    })
    print(f"Chat Response Status Code: {r_ask.status_code}")
    ans_data = r_ask.json()
    print(f"Bot Answer:\n{ans_data.get('answer')}\n")
    
    assert r_ask.status_code == 200
    assert any(word in ans_data.get('answer').lower() for word in ["api management", "serverless", "dynamic configurations", "database optimization"])
    print("--- ALL DYNAMIC UPLOAD TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    test_dynamic_config_upload()
