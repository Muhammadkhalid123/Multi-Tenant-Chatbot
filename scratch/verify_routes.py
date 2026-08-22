import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

client = app.test_client()

# 1. Test root redirect
res = client.get("/")
print("GET / -> Status:", res.status_code, "Location:", res.headers.get("Location"), flush=True)
assert res.status_code in [301, 302]
assert "/admin/dashboard" in res.headers.get("Location", "")

# 2. Test Super Admin dashboard
res = client.get("/admin/dashboard")
print("GET /admin/dashboard -> Status:", res.status_code, flush=True)
assert res.status_code == 200
assert b"ChatPulse" in res.data
assert b"clay-shadow" in res.data

# 3. Test Add Brand wizard
res = client.get("/admin/brand/new")
print("GET /admin/brand/new -> Status:", res.status_code, flush=True)
assert res.status_code == 200
assert b"Add New Brand" in res.data

# 4. Test Brand Detail page
res = client.get("/admin/brand/tecwrites")
print("GET /admin/brand/tecwrites -> Status:", res.status_code, flush=True)
assert res.status_code == 200
assert b"tecwrites" in res.data

# 5. Test Tenant dashboard
res = client.get("/tenant/dashboard?bot_id=tecwrites")
print("GET /tenant/dashboard -> Status:", res.status_code, flush=True)
assert res.status_code == 200

# 6. Test Legacy Redirects
res = client.get("/superadmin")
print("GET /superadmin -> Status:", res.status_code, "Location:", res.headers.get("Location"), flush=True)
assert res.status_code in [301, 302]

res = client.get("/tenant/tecwrites")
print("GET /tenant/tecwrites -> Status:", res.status_code, "Location:", res.headers.get("Location"), flush=True)
assert res.status_code in [301, 302]

# 7. Test API endpoints
res = client.get("/api/admin/brands")
print("GET /api/admin/brands -> Status:", res.status_code, flush=True)
assert res.status_code == 200

print("\n--- ALL CLAYMORPHISM ROUTES & REDIRECTS PASSED SUCCESSFULLY! ---", flush=True)
