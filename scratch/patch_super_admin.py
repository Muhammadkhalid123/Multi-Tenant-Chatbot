import os
import re

app_py_path = "app.py"
with open(app_py_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add HTML templates for Super Admin
# Find the end of ADMIN_DETAIL_HTML
admin_detail_end = code.find("</html>\"\"\"") + len("</html>\"\"\"")

SUPER_ADMIN_TEMPLATES = """

# -------------------------
# Super Admin Dashboard HTML Templates
# -------------------------
SUPER_ADMIN_LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Super Admin Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --primary: #3b82f6; --text: #f8fafc; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); color: var(--text); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: var(--card); padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; text-align: center; }
        input { width: 100%; padding: 12px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; border-radius: 8px; border: none; background: var(--primary); color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #2563eb; }
        .error { color: #ef4444; font-size: 14px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Master Dashboard</h2>
        <p style="color:#94a3b8; margin-bottom: 30px;">Login to manage all brands</p>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required autofocus>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
        </form>
    </div>
</body>
</html>'''

SUPER_ADMIN_LAYOUT = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SaaS Master Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --primary: #3b82f6; --text: #f8fafc; --muted: #94a3b8; --border: #334155; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; min-height: 100vh; }
        .sidebar { width: 250px; background: var(--card); border-right: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; }
        .sidebar h2 { font-size: 18px; margin-bottom: 30px; color: white; }
        .nav-link { padding: 12px 16px; color: var(--muted); text-decoration: none; border-radius: 8px; margin-bottom: 8px; font-weight: 600; }
        .nav-link:hover, .nav-link.active { background: rgba(59, 130, 246, 0.1); color: var(--primary); }
        .content { flex: 1; padding: 40px; overflow-y: auto; }
        h1 { margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: var(--card); border-radius: 8px; overflow: hidden; }
        th, td { padding: 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { font-size: 12px; text-transform: uppercase; color: var(--muted); }
        .badge { padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .badge.active { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
        .badge.suspended { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .btn { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; text-decoration: none; display: inline-block; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-warning { background: #f59e0b; color: white; }
        .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; z-index: 50; }
        .modal.open { display: flex; }
        .modal-content { background: var(--card); padding: 30px; border-radius: 12px; width: 400px; max-height: 90vh; overflow-y: auto;}
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-size: 14px; color: var(--muted); }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: white; box-sizing: border-box;}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>🚀 SaaS Master</h2>
        <a href="/superadmin/leads" class="nav-link {% if active_tab == 'leads' %}active{% endif %}">All Leads</a>
        <a href="/superadmin/brands" class="nav-link {% if active_tab == 'brands' %}active{% endif %}">Manage Brands</a>
        <div style="flex: 1;"></div>
        <a href="/superadmin/logout" class="nav-link" style="color: #ef4444;">Log Out</a>
    </div>
    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>'''

SUPER_ADMIN_LEADS_HTML = SUPER_ADMIN_LAYOUT + '''
{% block content %}
<h1>All Captured Leads</h1>
<table>
    <thead>
        <tr>
            <th>Date</th>
            <th>Brand (Bot ID)</th>
            <th>Name</th>
            <th>Contact</th>
            <th>Summary</th>
        </tr>
    </thead>
    <tbody>
        {% for chat in chats %}
        <tr>
            <td>{{ chat.started_at }}</td>
            <td style="color: var(--primary); font-weight: bold;">{{ chat.bot_id }}</td>
            <td>{{ chat.name }}</td>
            <td>{{ chat.email }}<br>{{ chat.phone }}</td>
            <td style="color: var(--muted); font-size: 14px;">{{ chat.summary }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
'''

SUPER_ADMIN_BRANDS_HTML = SUPER_ADMIN_LAYOUT + '''
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center;">
    <h1>Managed Brands</h1>
    <button class="btn btn-primary" onclick="document.getElementById('addModal').classList.add('open')">+ Add Brand</button>
</div>
<table>
    <thead>
        <tr>
            <th>Bot ID</th>
            <th>Brand Name</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for brand in brands %}
        <tr>
            <td style="font-weight: bold;">{{ brand.bot_id }}</td>
            <td>{{ brand.brand_name }}</td>
            <td>
                {% if brand.is_active != False %}
                <span class="badge active">Active</span>
                {% else %}
                <span class="badge suspended">Suspended</span>
                {% endif %}
            </td>
            <td style="display: flex; gap: 10px;">
                <form action="/superadmin/brands/{{ brand.bot_id }}/toggle" method="POST" style="margin:0;">
                    {% if brand.is_active != False %}
                    <button class="btn btn-warning" type="submit">Suspend</button>
                    {% else %}
                    <button class="btn btn-primary" type="submit" style="background:#10b981;">Activate</button>
                    {% endif %}
                </form>
                <form action="/superadmin/brands/{{ brand.bot_id }}/delete" method="POST" style="margin:0;" onsubmit="return confirm('Delete this brand permanently?');">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<div id="addModal" class="modal">
    <div class="modal-content">
        <h2 style="margin-top:0;">Add New Brand</h2>
        <form action="/superadmin/brands/add" method="POST">
            <div class="form-group">
                <label>Bot ID (e.g. my_brand)</label>
                <input type="text" name="bot_id" required>
            </div>
            <div class="form-group">
                <label>Brand Name</label>
                <input type="text" name="brand_name" required>
            </div>
            <div class="form-group">
                <label>Admin Username</label>
                <input type="text" name="admin_username" required>
            </div>
            <div class="form-group">
                <label>Admin Password</label>
                <input type="text" name="admin_password" required>
            </div>
            <div class="form-group">
                <label>System Prompt</label>
                <textarea name="system_prompt" rows="8" required>You are a helpful assistant for {brand_name}.

IMPORTANT FORMAT INSTRUCTIONS: You MUST always respond with a valid JSON object containing exactly these three keys:
1. "reply": (string) Your conversational response to the user.
2. "lead_required": (boolean) true if you need to capture their contact info, false otherwise.
3. "extracted_name": (string or null) the user's name if they provided it.

Context: {context}
Previous conversation: {history}
Question: {question}
JSON Response:</textarea>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="button" class="btn" style="background: var(--card); border: 1px solid var(--border); color: white;" onclick="document.getElementById('addModal').classList.remove('open')">Cancel</button>
                <button type="submit" class="btn btn-primary" style="flex:1;">Create Brand</button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
'''
"""

code = code[:admin_detail_end] + SUPER_ADMIN_TEMPLATES + code[admin_detail_end:]


# 2. Add Super Admin Routes
# Find the end of admin_logout
admin_logout_end = code.find("def admin_logout(bot_id):")
admin_logout_end = code.find("return redirect(url_for(\"admin_login\", bot_id=bot_id))", admin_logout_end) + len("return redirect(url_for(\"admin_login\", bot_id=bot_id))")

SUPER_ADMIN_ROUTES = """

# -------------------------
# Super Admin Portal (Master SaaS Dashboard)
# -------------------------
@app.route("/superadmin", methods=["GET", "POST"])
def superadmin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        master_pass = os.getenv("ADMIN_PASSWORD", "Pak123@#")
        if username == "superadmin" and password == master_pass:
            session["superadmin_logged_in"] = True
            return redirect(url_for("superadmin_brands"))
        else:
            error = "Invalid master credentials"
    return render_template_string(SUPER_ADMIN_LOGIN_HTML, error=error)

@app.route("/superadmin/leads", methods=["GET"])
def superadmin_leads():
    if not session.get("superadmin_logged_in"):
        return redirect(url_for("superadmin_login"))
    chats = list(db.chats.find().sort("started_at", -1))
    return render_template_string(SUPER_ADMIN_LEADS_HTML, chats=chats, active_tab='leads')

@app.route("/superadmin/brands", methods=["GET"])
def superadmin_brands():
    if not session.get("superadmin_logged_in"):
        return redirect(url_for("superadmin_login"))
    brands = list(db.bot_configs.find().sort("brand_name", 1))
    return render_template_string(SUPER_ADMIN_BRANDS_HTML, brands=brands, active_tab='brands')

@app.route("/superadmin/brands/add", methods=["POST"])
def superadmin_add_brand():
    if not session.get("superadmin_logged_in"):
        return redirect(url_for("superadmin_login"))
    
    bot_id = request.form.get("bot_id", "").strip()
    brand_name = request.form.get("brand_name", "").strip()
    admin_username = request.form.get("admin_username", "").strip()
    admin_password = request.form.get("admin_password", "").strip()
    system_prompt = request.form.get("system_prompt", "").strip()
    
    if bot_id:
        db.bot_configs.update_one(
            {"bot_id": bot_id},
            {"$set": {
                "brand_name": brand_name,
                "admin_username": admin_username,
                "admin_password": generate_password_hash(admin_password) if admin_password else None,
                "system_prompt": system_prompt.replace("{brand_name}", brand_name),
                "is_active": True
            }},
            upsert=True
        )
        if bot_id in _config_cache:
            del _config_cache[bot_id]
            
    return redirect(url_for("superadmin_brands"))

@app.route("/superadmin/brands/<bot_id>/toggle", methods=["POST"])
def superadmin_toggle_brand(bot_id):
    if not session.get("superadmin_logged_in"):
        return redirect(url_for("superadmin_login"))
    
    brand = db.bot_configs.find_one({"bot_id": bot_id})
    if brand:
        new_status = False if brand.get("is_active", True) else True
        db.bot_configs.update_one({"bot_id": bot_id}, {"$set": {"is_active": new_status}})
        if bot_id in _config_cache:
            del _config_cache[bot_id]
            
    return redirect(url_for("superadmin_brands"))

@app.route("/superadmin/brands/<bot_id>/delete", methods=["POST"])
def superadmin_delete_brand(bot_id):
    if not session.get("superadmin_logged_in"):
        return redirect(url_for("superadmin_login"))
    
    db.bot_configs.delete_one({"bot_id": bot_id})
    # Optionally delete chats: db.chats.delete_many({"bot_id": bot_id})
    if bot_id in _config_cache:
        del _config_cache[bot_id]
        
    return redirect(url_for("superadmin_brands"))

@app.route("/superadmin/logout", methods=["GET"])
def superadmin_logout():
    session.pop("superadmin_logged_in", None)
    return redirect(url_for("superadmin_login"))
"""

code = code[:admin_logout_end] + SUPER_ADMIN_ROUTES + code[admin_logout_end:]


# 3. Add Kill switch to /ask
ask_start = code.find("def ask():")
ask_config = code.find("config = load_bot_config(bot_id)", ask_start)
ask_config_end = code.find("\\n", ask_config) + 1

KILL_SWITCH = """
    if config.get("is_active") is False:
        return jsonify({
            "reply": "This assistant is currently unavailable.",
            "lead_required": False,
            "extracted_name": None
        })
"""

code = code[:ask_config_end] + KILL_SWITCH + code[ask_config_end:]

# 4. Add Kill switch to /widget
widget_start = code.find("def widget():")
widget_end = code.find("return send_from_directory('frontend', 'widget.html')", widget_start)
WIDGET_CHECK = """
    bot_id = request.args.get("bot_id")
    if bot_id:
        config = load_bot_config(bot_id)
        if config.get("is_active") is False:
            return "This assistant is currently suspended.", 403
    """
code = code[:widget_end] + WIDGET_CHECK + code[widget_end:]

with open(app_py_path, "w", encoding="utf-8") as f:
    f.write(code)
print("Successfully patched app.py with Super Admin features!")
