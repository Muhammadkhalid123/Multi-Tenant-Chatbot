import requests
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:5000"

def test_lead_saving():
    bot_id = "dynamic_api_brand"
    session_id = "session_lead_save_test_888"
    
    print("--- 1. Simulating Chat Conversation to build Transcript ---")
    requests.post(f"{BASE_URL}/clear_session", json={"session_id": session_id, "bot_id": bot_id})
    
    # Send a message to build history
    requests.post(f"{BASE_URL}/ask", json={
        "question": "Hello, my name is John Doe.",
        "session_id": session_id,
        "bot_id": bot_id
    })
    
    requests.post(f"{BASE_URL}/ask", json={
        "question": "I am interested in database optimization consulting.",
        "session_id": session_id,
        "bot_id": bot_id
    })
    
    print("--- 2. Submitting Lead Form ---")
    lead_payload = {
        "name": "John Doe",
        "email": "johndoe@example.com",
        "phone": "+1-555-0199",
        "session_id": session_id,
        "bot_id": bot_id
    }
    
    r_lead = requests.post(f"{BASE_URL}/lead", json=lead_payload)
    print(f"Lead Submission Status Code: {r_lead.status_code}")
    print(f"Lead Submission Response: {r_lead.json()}\n")
    
    assert r_lead.status_code == 200
    
    print("--- 3. Querying MongoDB Atlas Directly to verify Storage ---")
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client.get_default_database()
    
    # Retrieve the lead from chats collection
    lead = db.chats.find_one({"email": "johndoe@example.com", "bot_id": bot_id})
    print(f"Lead document found in MongoDB Atlas:")
    print(f"  Name: {lead.get('name')}")
    print(f"  Email: {lead.get('email')}")
    print(f"  Phone: {lead.get('phone')}")
    print(f"  Bot Source: {lead.get('bot_id')}")
    print(f"  Summary: {lead.get('summary')}")
    print(f"  Transcript preview:\n{lead.get('transcript')}\n")
    
    assert lead is not None
    assert lead.get("name") == "John Doe"
    print("--- LEAD SAVED TO MONGODB ATLAS SUCCESSFULLY! ---")

if __name__ == "__main__":
    test_lead_saving()
