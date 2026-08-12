import os
import json
import secrets
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import glob

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
client = MongoClient(MONGO_URI)
db = client.get_default_database()

def migrate():
    # Back up existing bot_configs if any
    if "bot_configs" in db.list_collection_names():
        configs = list(db.bot_configs.find())
        if configs:
            if "bot_configs_backup" in db.list_collection_names():
                db.bot_configs_backup.drop()
            db.bot_configs_backup.insert_many(configs)
            print(f"Backed up {len(configs)} bot_configs to bot_configs_backup")

    tenants_col = db.tenants
    
    config_files = glob.glob("config/*.json")
    for filepath in config_files:
        bot_id = os.path.basename(filepath).replace(".json", "")
        
        with open(filepath, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
        # Add new SaaS fields
        config_data["bot_id"] = bot_id
        config_data["status"] = "active"
        config_data["widget_api_key"] = f"sk_{bot_id}_{secrets.token_urlsafe(16)}"
        config_data["created_at"] = datetime.utcnow()
        if "usage" not in config_data:
            config_data["usage"] = {
                "total_messages": 0,
                "total_leads": 0
            }
        
        # Upsert by bot_id to avoid duplicates if run multiple times
        tenants_col.update_one(
            {"bot_id": bot_id},
            {"$set": config_data},
            upsert=True
        )
        print(f"Migrated tenant: {bot_id}")

if __name__ == "__main__":
    migrate()
    print("Migration complete. Verifying records...")
    for tenant in db.tenants.find():
        print(f"Verified: {tenant['bot_id']} - status: {tenant.get('status')} - webhook: {tenant.get('webhook_url')}")
