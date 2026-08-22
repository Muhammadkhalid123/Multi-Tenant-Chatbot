import os
import secrets
from pymongo import MongoClient

# Use the exact string from .env
MONGO_URI = "mongodb+srv://selfpublishingconsultants_db_user:yfom9fXQWk0lTsU9@cluster0.0hhmb5n.mongodb.net/chatbot?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client.get_default_database()

# Check if there is already a widget_api_key
config = db.bot_configs.find_one({"bot_id": "indie_global"})
if config:
    current_key = config.get("widget_api_key")
    if not current_key:
        new_key = secrets.token_hex(16)
        db.bot_configs.update_one(
            {"bot_id": "indie_global"},
            {"$set": {"widget_api_key": new_key}}
        )
        print(f"Generated new widget_api_key: {new_key}")
    else:
        print(f"Existing widget_api_key: {current_key}")
else:
    print("Bot config 'indie_global' not found.")
