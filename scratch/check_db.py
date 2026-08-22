import os
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://selfpublishingconsultants_db_user:yfom9fXQWk0lTsU9@cluster0.0hhmb5n.mongodb.net/chatbot?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client.get_default_database()

tenant = db.tenants.find_one({"bot_id": "indie_global"})
if tenant:
    for k, v in tenant.items():
        print(f"{k}: {v}")
