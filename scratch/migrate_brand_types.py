import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
print(f"[INFO] Connecting to MongoDB: {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI}")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.get_default_database()

BRAND_TYPE_MAP = {
    "indie_global": "ebook",
    "self_publishing": "ebook",
    "tecwrites": "hybrid",
    "influitivezone_api": "design"
}

def migrate_tenants():
    print("\n--- Migrating Brand Types in db.tenants and db.bot_configs ---")
    for bot_id, brand_type in BRAND_TYPE_MAP.items():
        # Update db.tenants
        t_res = db.tenants.update_one(
            {"bot_id": bot_id},
            {"$set": {"brand_type": brand_type, "brand_facts": ""}},
            upsert=False
        )
        # Update db.bot_configs
        b_res = db.bot_configs.update_one(
            {"bot_id": bot_id},
            {"$set": {"brand_type": brand_type, "brand_facts": ""}},
            upsert=False
        )
        print(f"[{bot_id}] Set brand_type='{brand_type}' (tenants modified: {t_res.modified_count}, bot_configs modified: {b_res.modified_count})")

    # Set default brand_type="ebook" on any other brand missing brand_type
    db.tenants.update_many({"brand_type": {"$exists": False}}, {"$set": {"brand_type": "ebook", "brand_facts": ""}})
    db.bot_configs.update_many({"brand_type": {"$exists": False}}, {"$set": {"brand_type": "ebook", "brand_facts": ""}})
    print("[OK] All existing brands backfilled successfully.")

if __name__ == "__main__":
    migrate_tenants()
