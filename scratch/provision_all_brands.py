import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
print(f"[INFO] Connecting to MongoDB: {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI}")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.get_default_database()

ALL_BRANDS = [
    {
        "bot_id": "indie_global",
        "brand_name": "Indie Global Publications",
        "website": "https://www.indieglobalpublications.com/",
        "brand_type": "ebook",
        "brand_facts": "Distributes to 40,000+ retail partners across 150+ countries. Authors retain 100% IP rights.",
        "primary_color": "#1a1a1a",
        "primary_light_color": "#4a4a4a",
        "welcome_message": "Hello! Welcome to Indie Global Publications. How can we help you turn your manuscript into a masterpiece today?",
        "owner_email": "admin@indieglobalpublications.com",
        "status": "active",
        "widget_api_key": "sk_indie_global_live"
    },
    {
        "bot_id": "kandle_direct",
        "brand_name": "Kandle Direct Publishing",
        "website": "https://www.kandledirectpublishing.com/",
        "brand_type": "ebook",
        "brand_facts": "Specializes in Amazon KDP optimization, Barnes & Noble, and IngramSpark global distribution.",
        "primary_color": "#ff9900",
        "primary_light_color": "#ffb84d",
        "welcome_message": "Welcome to Kandle Direct Publishing! How can we assist you with editing, cover design, or distributing your book worldwide today?",
        "owner_email": "admin@kandledirectpublishing.com",
        "status": "active",
        "widget_api_key": "sk_kandle_direct_live"
    },
    {
        "bot_id": "self_publishing",
        "brand_name": "Self Publishing Consultant",
        "website": "https://www.selfpublishingconsultant.com/",
        "brand_type": "ebook",
        "brand_facts": "End-to-end manuscript assessment, developmental editing, bespoke cover design, and full royalty tracking.",
        "primary_color": "#064e3b",
        "primary_light_color": "#0d9488",
        "welcome_message": "Hello! Welcome to Self Publishing Consultant. How can we help you publish and distribute your book today?",
        "owner_email": "admin@selfpublishingconsultant.com",
        "status": "active",
        "widget_api_key": "sk_self_publishing_live"
    },
    {
        "bot_id": "influitivezone",
        "brand_name": "Influitive Zone",
        "website": "https://www.influitivezone.com/digital-agency",
        "brand_type": "design",
        "brand_facts": "Full-service digital agency: high-converting web development, SEO, paid social ads, and UAE/international business setup.",
        "primary_color": "#2563eb",
        "primary_light_color": "#60a5fa",
        "welcome_message": "Welcome to Influitive Zone Digital Agency! How can we accelerate your online growth and digital presence today?",
        "owner_email": "admin@influitivezone.com",
        "status": "active",
        "widget_api_key": "sk_influitivezone_live"
    },
    {
        "bot_id": "tecwrites",
        "brand_name": "TecWrites",
        "website": "https://www.tecwrites.com/",
        "brand_type": "hybrid",
        "brand_facts": "Combines deep technical writing, developer documentation, and API guides with web development and digital branding.",
        "primary_color": "#0f766e",
        "primary_light_color": "#14b8a6",
        "welcome_message": "Welcome to TecWrites! How can our technical writing and digital engineering team assist your project today?",
        "owner_email": "admin@tecwrites.com",
        "status": "active",
        "widget_api_key": "sk_tecwrites_live"
    }
]

def provision_brands():
    print("\n--- Provisioning All 5 Target Brands in MongoDB ---")
    for b in ALL_BRANDS:
        bot_id = b["bot_id"]
        
        doc = {
            "bot_id": bot_id,
            "brand_name": b["brand_name"],
            "website": b["website"],
            "brand_type": b["brand_type"],
            "brand_facts": b["brand_facts"],
            "primary_color": b["primary_color"],
            "primary_light_color": b["primary_light_color"],
            "welcome_message": b["welcome_message"],
            "owner_email": b["owner_email"],
            "status": b["status"],
            "widget_api_key": b["widget_api_key"],
            "system_prompt": None,  # Use type-based curated template
            "webhook_url": None,
            "usage": {
                "total_messages": 0,
                "total_leads": 0
            }
        }
        
        # Upsert in db.tenants
        db.tenants.replace_one({"bot_id": bot_id}, doc, upsert=True)
        # Upsert in db.bot_configs
        db.bot_configs.replace_one({"bot_id": bot_id}, doc, upsert=True)
        
        print(f"[OK] Brand '{b['brand_name']}' ({bot_id}) provisioned -> Type: {b['brand_type']}")

    print("\n[SUCCESS] All 5 brands are now fully provisioned and active in MongoDB!")

if __name__ == "__main__":
    provision_brands()
