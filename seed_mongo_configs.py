import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
print(f"[INFO] Connecting to MongoDB: {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI}")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.get_default_database()

def seed_configs():
    config_dir = "config"
    if not os.path.exists(config_dir):
        print(f"[ERROR] Config directory '{config_dir}' not found.")
        return

    json_files = [f for f in os.listdir(config_dir) if f.endswith(".json")]
    if not json_files:
        print("[WARN] No JSON files found in config/ directory.")
        return

    for filename in json_files:
        file_path = os.path.join(config_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            bot_id = data.get("bot_id")
            if not bot_id:
                # Fallback to filename without extension
                bot_id = os.path.splitext(filename)[0]
                data["bot_id"] = bot_id
            
            # Print configuration info
            print(f"[INFO] Seeding configuration for '{bot_id}' from {filename}...")

            # Clean and prepare fields to match expected schema in MongoDB
            tenant_doc = {
                "bot_id": bot_id,
                "brand_name": data.get("brand_name", bot_id.replace("_", " ").title()),
                "welcome_message": data.get("welcome_message", f"Hello! Welcome to {bot_id.replace('_', ' ').title()}."),
                "primary_color": data.get("primary_color", "#d97706"),
                "primary_light_color": data.get("primary_light_color", "#fbbf24"),
                "webhook_url": data.get("webhook_url"),
                "system_prompt": data.get("system_prompt"),
                "admin_username": data.get("admin_username"),
                "admin_password": data.get("admin_password")
            }

            # Upsert into bot_configs collection
            db.bot_configs.replace_one(
                {"bot_id": bot_id},
                tenant_doc,
                upsert=True
            )
            
            # Upsert into tenants collection as well
            db.tenants.update_one(
                {"bot_id": bot_id},
                {"$set": {
                    "brand_name": tenant_doc["brand_name"],
                    "welcome_message": tenant_doc["welcome_message"],
                    "primary_color": tenant_doc["primary_color"],
                    "primary_light_color": tenant_doc["primary_light_color"],
                    "webhook_url": tenant_doc["webhook_url"],
                    "system_prompt": tenant_doc["system_prompt"],
                    "status": "active"
                },
                "$setOnInsert": {
                    "widget_api_key": f"sk_{bot_id}_live",
                    "created_at": "2026-08-22"
                }},
                upsert=True
            )
            print(f"[OK] Configuration for '{bot_id}' successfully upserted into db.bot_configs and db.tenants.")
        except Exception as e:
            print(f"[ERROR] Failed to seed {filename}: {e}")

if __name__ == "__main__":
    seed_configs()
