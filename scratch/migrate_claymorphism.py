import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove legacy HTML templates (from ADMIN_LOGIN_HTML = ... up to right before creation_limiter_key)
# Find start
start_marker = "# -------------------------\n# Admin Dashboard HTML Templates\n# -------------------------"
end_marker = "# -------------------------\n# Dynamic Configuration Upload Endpoint\n# -------------------------"

if start_marker in content and end_marker in content:
    idx1 = content.find(start_marker)
    idx2 = content.find(end_marker)
    replacement = """# -------------------------
# Admin Dashboard (Claymorphism SaaS UI)
# -------------------------

"""
    content = content[:idx1] + replacement + content[idx2:]
    print("Successfully removed inline HTML templates!")
else:
    print("Could not find exact template markers, checking regex...")

# 2. Update the Admin routes section
legacy_admin_routes_start = "# -------------------------\n# Admin Portal Routes\n# -------------------------"
debug_endpoints_start = "# -------------------------\n# Debug endpoints\n# -------------------------"

if legacy_admin_routes_start in content and debug_endpoints_start in content:
    idx_routes1 = content.find(legacy_admin_routes_start)
    idx_routes2 = content.find(debug_endpoints_start)
    
    new_routes = """# -------------------------
# Claymorphism SaaS Dashboard Routes
# -------------------------
@app.route("/admin/dashboard", methods=["GET"])
@app.route("/admin", methods=["GET"])
def saas_admin_dashboard():
    \"\"\"Serves the Claymorphism Super Admin Brands Overview\"\"\"
    try:
        brands = list(db.tenants.find().sort("created_at", -1))
        if not brands:
            brands = list(db.bot_configs.find().sort("brand_name", 1))
            
        active_count = sum(1 for b in brands if b.get("status") == "active" or (b.get("status") is None and b.get("is_active", True) is True))
        suspended_count = sum(1 for b in brands if b.get("status") == "suspended" or b.get("is_active") is False)
        total_leads = db.chats.count_documents({})
        
        stats = {
            "active_brands": active_count,
            "suspended_brands": suspended_count,
            "total_leads": total_leads,
            "mrr": f"${active_count * 49}"
        }
    except Exception as e:
        print(f"[ERROR] Failed to load dashboard data: {e}")
        brands = []
        stats = {"active_brands": 0, "suspended_brands": 0, "total_leads": 0, "mrr": "$0"}
        
    return render_template("admin/super_dashboard.html", brands=brands, stats=stats)

@app.route("/admin/brand/new", methods=["GET"])
def saas_admin_add_brand():
    \"\"\"Serves the Claymorphism Add Brand Wizard\"\"\"
    return render_template("admin/add_brand.html")

@app.route("/admin/brand/<bot_id>", methods=["GET"])
@app.route("/admin/<bot_id>", methods=["GET"])
def saas_admin_brand_detail(bot_id):
    \"\"\"Serves the Claymorphism Brand Detail & Config Panel\"\"\"
    brand = db.tenants.find_one({"bot_id": bot_id})
    if not brand:
        brand = db.bot_configs.find_one({"bot_id": bot_id})
    if not brand:
        brand = _default_config(bot_id)
        
    try:
        total_chats = db.chats.count_documents({"bot_id": bot_id})
        leads = list(db.chats.find({"bot_id": bot_id}).sort("started_at", -1).limit(50))
        for l in leads:
            l["id"] = str(l["_id"])
    except Exception as e:
        print(f"[ERROR] Failed to load brand detail data for {bot_id}: {e}")
        total_chats = 0
        leads = []
        
    stats = {
        "total_messages": total_chats,
        "total_leads": len(leads)
    }
    return render_template("admin/brand_detail.html", brand=brand, bot_id=bot_id, leads=leads, stats=stats)

@app.route("/tenant/dashboard", methods=["GET"])
def saas_tenant_dashboard():
    \"\"\"Serves the Claymorphism Tenant / Brand Admin Dashboard\"\"\"
    bot_id = request.args.get("bot_id", "tecwrites")
    brand = load_bot_config(bot_id)
    try:
        leads = list(db.chats.find({"bot_id": bot_id}).sort("started_at", -1).limit(50))
        for l in leads:
            l["id"] = str(l["_id"])
    except Exception as e:
        leads = []
    return render_template("admin/tenant_dashboard.html", brand=brand, bot_id=bot_id, leads=leads)

# Backward Compatibility / Redirects to Claymorphism Dashboard
@app.route("/superadmin", methods=["GET", "POST"])
@app.route("/superadmin/leads", methods=["GET"])
@app.route("/superadmin/brands", methods=["GET"])
def legacy_superadmin_redirect():
    return redirect(url_for("saas_admin_dashboard"))

@app.route("/tenant/<bot_id>", methods=["GET", "POST"])
@app.route("/tenant/<bot_id>/chats", methods=["GET"])
@app.route("/tenant/<bot_id>/chats/<chat_id>", methods=["GET"])
def legacy_tenant_redirect(bot_id, chat_id=None):
    return redirect(url_for("saas_admin_brand_detail", bot_id=bot_id))

# -------------------------
# Widget & Frontend Asset Routes
# -------------------------
@app.route("/widget", methods=["GET"])
def widget():
    bot_id = request.args.get("bot_id")
    if bot_id:
        config = load_bot_config(bot_id)
        if config.get("status") == "suspended" or config.get("is_active") is False:
            return render_template('widget_suspended.html'), 403
    return send_from_directory('frontend', 'widget.html')

@app.route("/frontend/<path:filename>", methods=["GET"])
def serve_frontend(filename):
    return send_from_directory('frontend', filename)

"""
    content = content[:idx_routes1] + new_routes + content[idx_routes2:]
    print("Successfully replaced legacy admin routes with Claymorphism routes!")
else:
    print("Could not find exact routes markers.")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("app.py updated.")
