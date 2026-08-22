import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompt_templates import build_system_prompt, extract_interests_from_message, TEMPLATES

print("\n--- 1. Testing build_system_prompt() ---", flush=True)

# E-book test
ebook_cfg = {"brand_name": "Starlight Books", "brand_type": "ebook", "brand_facts": "Specializes in sci-fi."}
ebook_prompt = build_system_prompt(ebook_cfg)
assert "publishing assistant for Starlight Books" in ebook_prompt, "Ebook brand name failed"
assert "Specializes in sci-fi." in ebook_prompt, "Ebook facts failed"
print("[OK] E-book prompt composed correctly.", flush=True)

# Design test
design_cfg = {"brand_name": "Pixel Wave Agency", "brand_type": "design", "brand_facts": "Offers UAE formation."}
design_prompt = build_system_prompt(design_cfg)
assert "digital strategy assistant for Pixel Wave Agency" in design_prompt, "Design brand name failed"
assert "Offers UAE formation." in design_prompt, "Design facts failed"
print("[OK] Design prompt composed correctly.", flush=True)

# Hybrid test
hybrid_cfg = {"brand_name": "TecWrites", "brand_type": "hybrid"}
hybrid_prompt = build_system_prompt(hybrid_cfg)
assert "assistant for TecWrites" in hybrid_prompt, "Hybrid brand name failed"
print("[OK] Hybrid prompt composed correctly.", flush=True)

# Escape hatch override test
override_cfg = {"brand_name": "Custom Bot", "system_prompt": "CUSTOM_PROMPT_OVERRIDE"}
override_prompt = build_system_prompt(override_cfg)
assert override_prompt == "CUSTOM_PROMPT_OVERRIDE", "Escape hatch failed"
print("[OK] Escape hatch override preserved correctly.", flush=True)

print("\n--- 2. Testing extract_interests_from_message() ---", flush=True)

# Design brand type
design_q = "I need SEO optimization, social media marketing, and a new website."
design_interests = extract_interests_from_message(design_q, brand_type="design")
print("Design interests extracted:", design_interests, flush=True)
assert "SEO & Organic Growth" in design_interests
assert "Web Development" in design_interests
assert "Social Media Marketing" in design_interests
print("[OK] Design interests extracted correctly.", flush=True)

# E-book brand type
ebook_q = "Can you help with manuscript assessment, developmental editing, and book cover design?"
ebook_interests = extract_interests_from_message(ebook_q, brand_type="ebook")
print("E-book interests extracted:", ebook_interests, flush=True)
assert "Manuscript Assessment" in ebook_interests
assert "Developmental Editing" in ebook_interests
assert "Cover Design" in ebook_interests
print("[OK] E-book interests extracted correctly.", flush=True)

print("\n==========================================", flush=True)
print("ALL PROMPT TEMPLATE TESTS PASSED!", flush=True)
print("==========================================\n", flush=True)
