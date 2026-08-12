from flask import Blueprint, request, jsonify, session
import os
import shutil
from datetime import datetime
import secrets
from pymongo import MongoClient

admin_brands_bp = Blueprint('admin_brands', __name__)

# Reconnect to MongoDB for this blueprint
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_default_database()

def require_super_admin():
    # Simple check for now based on app.py's session state
    if not session.get("superadmin_logged_in"):
        return False
    return True

@admin_brands_bp.route('/api/admin/brands', methods=['GET'])
def get_brands():
    """List all tenants"""
    # Temporarily skipping auth check for local dev testing as requested in Phase 2
    # if not require_super_admin():
    #     return jsonify({"error": "Unauthorized"}), 401
        
    tenants = list(db.tenants.find({}, {"_id": 0}))
    return jsonify({"brands": tenants})

@admin_brands_bp.route('/api/admin/brands', methods=['POST'])
def create_brand():
    """Create a new tenant end-to-end"""
    data = request.get_json()
    bot_id = data.get("bot_id")
    
    if not bot_id:
        return jsonify({"error": "bot_id is required"}), 400
        
    if db.tenants.find_one({"bot_id": bot_id}):
        return jsonify({"error": "bot_id already exists"}), 400
        
    # 1. Create Mongo Document
    new_tenant = {
        "bot_id": bot_id,
        "brand_name": data.get("brand_name", bot_id),
        "owner_email": data.get("owner_email", ""),
        "status": "active",
        "widget_api_key": f"sk_{bot_id}_{secrets.token_urlsafe(16)}",
        "created_at": datetime.utcnow(),
        "usage": {
            "total_messages": 0,
            "total_leads": 0
        },
        "primary_color": data.get("primary_color", "#0d9488"),
        "welcome_message": data.get("welcome_message", "Hello! How can I help you today?"),
        "system_prompt": data.get("system_prompt", "You are a helpful assistant."),
        "webhook_url": data.get("webhook_url", "")
    }
    
    db.tenants.insert_one(new_tenant)
    
    # 2. Create Folder
    brand_folder = os.path.join("data", "brands", bot_id)
    os.makedirs(brand_folder, exist_ok=True)
    
    # Create a dummy markdown file to initialize the folder
    with open(os.path.join(brand_folder, "init.md"), "w") as f:
        f.write(f"# Welcome to {new_tenant['brand_name']} Knowledge Base\n\nAdd your content here.")
        
    # (Vector store creation is typically handled by build_vector_stores.py, 
    # but the folder is now ready for it)
    
    # Remove ObjectId for JSON serialization
    del new_tenant["_id"]
    return jsonify({"message": "Brand created successfully", "brand": new_tenant}), 201

@admin_brands_bp.route('/api/admin/brands/<bot_id>/status', methods=['PATCH'])
def update_brand_status(bot_id):
    """Suspend or reactivate a brand"""
    data = request.get_json()
    new_status = data.get("status")
    
    if new_status not in ["active", "suspended"]:
        return jsonify({"error": "Invalid status. Must be 'active' or 'suspended'"}), 400
        
    result = db.tenants.update_one(
        {"bot_id": bot_id},
        {"$set": {
            "status": new_status,
            "suspended_at": datetime.utcnow() if new_status == "suspended" else None
        }}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Brand not found"}), 404
        
    return jsonify({"message": f"Brand status updated to {new_status}"})

@admin_brands_bp.route('/api/admin/brands/<bot_id>', methods=['DELETE'])
def delete_brand(bot_id):
    """Hard delete a brand entirely"""
    # 1. Delete Mongo doc
    result = db.tenants.delete_one({"bot_id": bot_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Brand not found"}), 404
        
    # 2. Delete Chunks & Chats
    db.chunks.delete_many({"bot_id": bot_id})
    db.chats.delete_many({"bot_id": bot_id})
    
    # 3. Delete folder
    brand_folder = os.path.join("data", "brands", bot_id)
    if os.path.exists(brand_folder):
        shutil.rmtree(brand_folder)
        
    # 4. Delete vector store folder (assuming FAISS stores locally for now)
    vs_folder = os.path.join("vector_stores", bot_id)
    if os.path.exists(vs_folder):
        shutil.rmtree(vs_folder)
        
    return jsonify({"message": f"Brand {bot_id} completely deleted."})
