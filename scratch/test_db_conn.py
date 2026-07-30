import os
import ssl
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi

load_dotenv()

MONGO_URI = "mongodb://localhost:27017/chatbot"
print("URI:", MONGO_URI)

print("--- Try 1: Standard client ---")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_default_database()
    print("Database:", db.name)
    print("Collections:", db.list_collection_names())
except Exception as e:
    print("Failed Try 1:", e)

print("--- Try 2: With certifi cafile ---")
try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = client.get_default_database()
    print("Database:", db.name)
    print("Collections:", db.list_collection_names())
except Exception as e:
    print("Failed Try 2:", e)

print("--- Try 3: tlsAllowInvalidCertificates=True ---")
try:
    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
    db = client.get_default_database()
    print("Database:", db.name)
    print("Collections:", db.list_collection_names())
except Exception as e:
    print("Failed Try 3:", e)
