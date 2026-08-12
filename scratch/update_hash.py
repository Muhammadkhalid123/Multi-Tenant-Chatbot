import json
from werkzeug.security import generate_password_hash, check_password_hash

# Correct password
pw = "Pak123@#"

# Create new hash safely without shell escaping issues
new_hash = generate_password_hash(pw)

print("Generated:", new_hash)
print("Matches?", check_password_hash(new_hash, pw))

# Let's also test against the hash currently in the JSON file
with open("config/tecwrites.json", "r") as f:
    config = json.load(f)
    print("In JSON:", config.get("admin_password"))
    print("Matches JSON?", check_password_hash(config.get("admin_password"), pw))

# Update the json file directly!
config["admin_password"] = new_hash
with open("config/tecwrites.json", "w") as f:
    json.dump(config, f, indent=2)
