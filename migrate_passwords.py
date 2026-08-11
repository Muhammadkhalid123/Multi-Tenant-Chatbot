import os
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_default_database()

def is_sha256_hash(hash_str: str) -> bool:
    if len(hash_str) != 64:
        return False
    try:
        int(hash_str, 16)
        return True
    except ValueError:
        return False

def migrate():
    print("Starting password hash migration check...")
    configs = db.bot_configs.find({"admin_password": {"$type": "string"}})
    legacy_count = 0
    plaintext_count = 0
    
    for config in configs:
        bot_id = config.get("bot_id")
        current_hash = config.get("admin_password")
        
        if not current_hash:
            continue
            
        if current_hash.startswith("scrypt:") or current_hash.startswith("pbkdf2:"):
            # Already migrated
            continue
            
        if is_sha256_hash(current_hash):
            print(f"[WARNING] Bot ID '{bot_id}' has a legacy SHA-256 password hash.")
            print(f"          This tenant must re-upload their config to generate a valid Werkzeug hash.")
            legacy_count += 1
        else:
            # Unhashed plaintext? (From before the very first fix)
            new_hash = generate_password_hash(current_hash)
            db.bot_configs.update_one({"_id": config["_id"]}, {"$set": {"admin_password": new_hash}})
            print(f"[OK] Migrated plaintext password to Werkzeug hash for bot_id: {bot_id}")
            plaintext_count += 1
                
    print(f"Migration check complete. {plaintext_count} plaintext passwords hashed. {legacy_count} legacy SHA-256 hashes require re-upload.")

if __name__ == "__main__":
    migrate()
