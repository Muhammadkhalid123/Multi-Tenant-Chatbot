import sys
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template_string, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from prompt_templates import build_system_prompt, extract_interests_from_message, TEMPLATES
import re
import json
import os
import glob
import requests
import sqlite3
import threading
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict
from pymongo import MongoClient
from bson.objectid import ObjectId
import secrets
import hashlib
import string
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import ipaddress
import socket
from urllib.parse import urlparse
import re
import hmac

BOT_ID_PATTERN = re.compile(r'^[a-z0-9_]{3,50}$')

def is_valid_bot_id(bot_id: str) -> bool:
    return bool(BOT_ID_PATTERN.match(bot_id))

load_dotenv()

# MongoDB Database Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = mongo_client.get_default_database()

app = Flask(__name__)

from admin_brands import admin_brands_bp
app.register_blueprint(admin_brands_bp)

# Restrict CORS to known origins if configured
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if "*" in allowed_origins:
    CORS(app)
else:
    CORS(app, origins=allowed_origins)

# Separate session signing secret from ADMIN_PASSWORD
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

def get_tenant_limiter_key():
    try:
        data = request.get_json(silent=True, force=True) or {}
        bot_id = data.get("bot_id", "unknown").strip()
    except Exception:
        bot_id = "unknown"
    return f"{bot_id}:{get_remote_address()}"

limiter = Limiter(
    get_tenant_limiter_key,
    app=app,
    storage_uri=os.getenv("REDIS_URL", "memory://"),
)

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def scoped_key(bot_id: str, session_id: str) -> str:
    return f"{bot_id}:{session_id}"

# -------------------------
# MongoDB Database Initialization
# -------------------------
def init_db():
    try:
        # Create indexes
        db.bot_configs.create_index("bot_id", unique=True)
        db.chats.create_index([("bot_id", 1), ("started_at", -1)])
        print("[INFO] MongoDB connected and indexes verified successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize MongoDB database: {e}")

init_db()

# -------------------------
# Multi-tenant Config & Atlas Vector Search
# -------------------------

# MongoDB collection for knowledge-base chunks
_chunks_col = db.chunks

# In-memory cache for tenant configs only (retrievers are no longer cached locally)
_config_cache = {}

# HuggingFace Inference API — used at query time to embed the user's question
_HF_API_URL = (
    "https://api-inference.huggingface.co/pipeline/feature-extraction/"
    "sentence-transformers/all-MiniLM-L6-v2"
)
_HF_HEADERS = (
    {"Authorization": f"Bearer {os.getenv('HF_TOKEN') or os.getenv('HF_API_KEY')}"}
    if (os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY"))
    else {}
)


def embed_query(text: str) -> list:
    """Embed a single query string via HuggingFace Inference API (384 dims)."""
    try:
        resp = requests.post(
            _HF_API_URL,
            headers=_HF_HEADERS,
            json={"inputs": [text], "options": {"wait_for_model": True}},
            timeout=10,
        )
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and result:
                if isinstance(result[0], list):
                    # result is [[float, ...]] or [[[float, ...]]]
                    return result[0][0] if isinstance(result[0][0], list) else result[0]
        print(f"[WARN] HF embed_query status {resp.status_code}: {resp.text}")
        raise RuntimeError(f"HF API returned {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] embed_query failed: {e}")
        raise


def embed_texts(texts: list) -> list:
    """Embed a batch of texts via HuggingFace Inference API (384 dims each)."""
    if not texts:
        return []
    try:
        resp = requests.post(
            _HF_API_URL,
            headers=_HF_HEADERS,
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=30,
        )
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and result:
                if isinstance(result[0], list):
                    return (
                        [r[0] for r in result]
                        if isinstance(result[0][0], list)
                        else result
                    )
        print(f"[WARN] HF embed_texts status {resp.status_code}: {resp.text}")
        raise RuntimeError(f"HF API returned {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] embed_texts failed: {e}")
        raise


def store_chunks_to_mongo(bot_id: str, texts: list, vectors: list, source: str = "upload"):
    """
    Replaces all chunks for bot_id in the Atlas 'chunks' collection.
    Enforces tenant isolation at the storage layer — not just in app logic.
    """
    _chunks_col.delete_many({"bot_id": bot_id})
    if not texts:
        return
    docs = [
        {"bot_id": bot_id, "text": text, "embedding": vector, "source": source}
        for text, vector in zip(texts, vectors)
    ]
    _chunks_col.insert_many(docs)
    print(f"[INFO] Stored {len(docs)} chunks in MongoDB for '{bot_id}'")


def retrieve_context(bot_id: str, query: str, top_k: int = 3) -> str:
    """
    Retrieves the top-k relevant knowledge-base chunks for a query using
    Atlas Vector Search ($vectorSearch). The bot_id filter provides
    tenant isolation at the query layer.
    Returns a single string with chunks joined by double newlines.
    """
    try:
        query_vector = embed_query(query)
    except Exception as e:
        print(f"[WARN] Skipping retrieval due to embedding failure: {e}")
        return ""
        
    try:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "chunk_vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 100,
                    "limit": top_k,
                    "filter": {"bot_id": {"$eq": bot_id}},
                }
            },
            {"$project": {"text": 1, "source": 1, "_id": 0}},
        ]
        results = list(_chunks_col.aggregate(pipeline))
        if results:
            return "\n\n".join(r["text"] for r in results)
    except Exception as e:
        print(f"[ERROR] Atlas $vectorSearch failed for '{bot_id}': {e}")
    return ""

def load_bot_config(bot_id):
    """Load configuration for a specific chatbot brand"""
    if bot_id in _config_cache:
        return _config_cache[bot_id]
        
    try:
        row = db.tenants.find_one({"bot_id": bot_id})
        if not row:
            row = db.bot_configs.find_one({"bot_id": bot_id})
        if row:
            # Remove MongoDB internal ObjectId
            row.pop("_id", None)
            # Compose system prompt dynamically from brand type template if not an explicit override
            row["system_prompt"] = build_system_prompt(row)
            _config_cache[bot_id] = row
            return row
    except Exception as e:
        print(f"[ERROR] Failed to load config from database for {bot_id}: {e}")
            
    # Fall back to default config values if not in DB
    cfg = _default_config(bot_id)
    cfg["system_prompt"] = build_system_prompt(cfg)
    return cfg

def _default_config(bot_id):
    return {
        "bot_id": bot_id,
        "brand_name": bot_id.replace("_", " ").title(),
        "brand_type": "ebook",
        "brand_facts": "",
        "welcome_message": f"Hello! Welcome to {bot_id.replace('_', ' ').title()} Chat Assistant. How can I help you today?",
        "primary_color": "#d97706",
        "primary_light_color": "#fbbf24",
        "webhook_url": None,
        "system_prompt": None
    }

# -------------------------
# LLM setup - Support Ollama and Groq (OpenAI-compatible)
# -------------------------
llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()

if llm_provider == "groq":
    print("[INFO] Initializing ChatOpenAI client for Groq...")
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    if groq_model == "llama-3.3-70b-versatile" or not groq_model:
        groq_model = "openai/gpt-oss-120b"
        
    llm = ChatOpenAI(
        openai_api_base=os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1"),
        openai_api_key=os.getenv("GROQ_API_KEY"),
        model_name=groq_model,
        temperature=0.7,
        model_kwargs={"response_format": {"type": "json_object"}}
    )
else:
    print("[INFO] Initializing OllamaLLM client...")
    llm = OllamaLLM(
        model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )



# Dynamic PromptTemplates are now loaded from bot config JSON files.


# Store conversation history and user names
chat_sessions = defaultdict(list)
user_names = {}   # session_id -> user's first name

# Track which services/packages a user has shown interest in during conversation
session_interests = defaultdict(set)  # session_id -> set of service/package names

# -------------------------
# -------------------------
# SIMPLE intent detection - not complex
# -------------------------
def detect_intent(question, history=""):
    """Simple intent detection"""
    q_lower = question.lower()
    
    # Human agent / call / contact signals - trigger lead form immediately
    human_signals = [
        "human agent", "human", "real person", "talk to someone", "speak to someone",
        "talk to agent", "talk on call", "want a call", "want to call", "call me",
        "phone call", "whatsapp", "contact you", "reach you", "speak with",
        "connect me", "get in touch", "i want to talk", "talk to a person",
        "is there any agent", "any agent", "live agent", "live support",
        "support agent", "agent"
    ]
    if any(signal in q_lower for signal in human_signals):
        return "human"

    # Informational questions about services
    if any(phrase in q_lower for phrase in ["what is", "what does", "tell me about", "explain"]):
        return "service_info"
    
    # Quote/consultation and new buy signals (robust pattern matching)
    buy_patterns = [
        lambda q: "get" in q and "quote" in q,
        lambda q: "want" in q and "quote" in q,
        lambda q: "interest" in q and "quote" in q,
        lambda q: "book" in q and "consult" in q,
        lambda q: "schedule" in q and "consult" in q,
        lambda q: "book" in q and "call" in q,
        lambda q: "schedule" in q and "call" in q,
        lambda q: "let" in q and "start" in q,
        lambda q: "sign" in q and "up" in q,
        lambda q: "ready" in q and "start" in q,
        lambda q: "proceed" in q,
        lambda q: "let's go" in q,
    ]
    
    if any(pattern(q_lower) for pattern in buy_patterns):
        return "buy"
    
    return "general"

# -------------------------
# Webhook Helper
# -------------------------
def is_safe_webhook_url(url: str) -> tuple[bool, str]:
    """
    Validates a tenant-supplied webhook URL to prevent SSRF.
    Returns (is_safe, reason_if_not).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Malformed URL"

    if parsed.scheme != "https":
        return False, "Only https:// URLs are allowed"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must include a hostname"

    blocked_hostnames = {"localhost", "metadata.google.internal"}
    if hostname.lower() in blocked_hostnames:
        return False, "Hostname is not allowed"

    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, "Hostname could not be resolved"

    for family, _, _, _, sockaddr in resolved_ips:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, "Invalid resolved IP"

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False, f"Resolved IP {ip_str} is in a blocked range"

    return True, ""

def send_to_webhook(name, email, phone, webhook_url):
    if not webhook_url:
        return
        
    safe, reason = is_safe_webhook_url(webhook_url)
    if not safe:
        print(f"[SECURITY] Blocked webhook call to unsafe URL: {reason}")
        return

    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "form_type": "Contact Form",
        "name": name,
        "email": email,
        "phone": phone
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=5, allow_redirects=False)
        print("[INFO] Successfully sent lead to Webhook.")
    except Exception as e:
        print(f"[ERROR] Failed to send lead to Webhook: {e}")

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return redirect(url_for("saas_admin_dashboard"))

def parse_llm_json_response(llm_output):
    """
    Parses the JSON response from the LLM.
    Returns (reply_text, lead_required_boolean, extracted_name_string_or_none).
    """
    clean_output = llm_output.strip()
    
    # Strip markdown code block wrappers if present
    if clean_output.startswith("```"):
        # Remove opening ```json or ```
        clean_output = re.sub(r'^```(?:json)?\n', '', clean_output, flags=re.IGNORECASE)
        # Remove closing ```
        clean_output = re.sub(r'\n```$', '', clean_output)
        clean_output = clean_output.strip()
        
    try:
        data = json.loads(clean_output)
        reply = data.get("reply", "").strip()
        lead_required = bool(data.get("lead_required", False))
        extracted_name = data.get("extracted_name")
        if isinstance(extracted_name, str):
            extracted_name = extracted_name.strip()
            if extracted_name.lower() in ("null", "none", ""):
                extracted_name = None
        else:
            extracted_name = None
        if reply:
            return reply, lead_required, extracted_name
    except Exception as e:
        print(f"[WARN] Failed to parse LLM response as JSON: {e}. Output was: {llm_output}")
        
    return llm_output, False, None

def safe_format_prompt(template_str, context, history, question, name_context=""):
    """
    Safely formats a system prompt template without crashing on unescaped JSON braces.
    """
    if not template_str:
        template_str = "You are a helpful assistant.\n\nContext: {context}\n\nPrevious conversation: {history}\n\nQuestion: {question}\n\nJSON Response:"
    
    full_context = (name_context + context).strip()
    
    try:
        pt = PromptTemplate(
            input_variables=["context", "history", "question"],
            template=template_str
        )
        return pt.format(context=full_context, history=history, question=question)
    except Exception:
        # Fallback to direct placeholder replacement if template contains unescaped single braces
        res = template_str
        res = res.replace("{context}", full_context)
        res = res.replace("{history}", history)
        res = res.replace("{question}", question)
        return res

@app.route("/ask", methods=["POST"])
@limiter.limit("30/minute")
def ask():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    session_id = data.get("session_id", "default")
    bot_id = data.get("bot_id", "self_publishing").strip()
    skey = scoped_key(bot_id, session_id)
    
    if not question:
        return jsonify({"error": "No message provided"}), 400

    # Load brand config
    config = load_bot_config(bot_id)
    
    # Validate Widget API Key if present
    incoming_key = request.headers.get("X-Widget-API-Key") or request.args.get("widget_api_key") or request.args.get("api_key") or data.get("api_key")
    configured_key = config.get("widget_api_key")
    if configured_key and incoming_key and incoming_key != configured_key:
        return jsonify({"error": "Unauthorized"}), 401
        
    # Check if tenant is suspended before making LLM calls
    if config.get("status") == "suspended" or config.get("is_active") is False:
        return jsonify({
            "reply": "This service is temporarily paused.",
            "answer": "This service is temporarily paused.",
            "lead_required": False,
            "extracted_name": None
        })

    # Track service interests from this message based on brand type
    new_interests = extract_interests_from_message(question, brand_type=config.get("brand_type", "ebook"))
    session_interests[skey].update(new_interests)

    # Get session history
    session_history = chat_sessions[skey]
    
    # Simple history text (last 3 exchanges only)
    history_text = "\n".join([f"User: {msg['user']}\nBot: {msg['bot']}" 
                              for msg in session_history[-3:]])
    
    # Get context from Atlas Vector Search
    context = ""
    try:
        context = retrieve_context(bot_id, question, top_k=3)
        context = context[:4000]  # Limit context size
    except Exception as e:
        print(f"[ERROR] Retrieval failed for {bot_id}: {e}")
    
    # Check for direct name response if we were awaiting a name
    is_awaiting_name = skey in user_names and user_names[skey] == "__awaiting__"
    if is_awaiting_name:
        name_match = re.search(r'(?:my name is|i am|i\'m|this is|call me)\s+([A-Za-z]+)', question, re.IGNORECASE)
        if name_match:
            user_names[skey] = name_match.group(1).capitalize()
        else:
            words = question.strip().split()
            if 1 <= len(words) <= 2 and words[0].isalpha():
                user_names[skey] = words[0].capitalize()
            else:
                user_names[skey] = ""

    # Inject the user's known name into the history context
    known_name = user_names.get(skey, "")
    name_context = f"The user's name is {known_name}. Use their name naturally in your replies.\n" if known_name and known_name != "__awaiting__" else ""

    # Build prompt dynamically using config prompt template safely
    prompt = safe_format_prompt(
        config.get("system_prompt"),
        context=context,
        history=history_text,
        question=question,
        name_context=name_context
    )
    
    lead_required = False
    try:
        # Get LLM response
        raw_answer = llm.invoke(prompt)
        if hasattr(raw_answer, 'content'):
            raw_answer = raw_answer.content
        raw_answer = raw_answer.strip()
        
        # Parse JSON response
        answer_text, lead_required, extracted_name = parse_llm_json_response(raw_answer)
        
        if extracted_name:
            user_names[skey] = extracted_name
        
    except Exception as e:
        print(f"[ERROR] LLM Invocation failed: {e}")
        import traceback
        traceback.print_exc()
        answer_text = f"I'm here to help with your {config.get('brand_name')} questions. How can I help you today?"
        lead_required = False
    
    # After very first exchange only: if name is completely unknown, ask for user's name politely
    is_first_message = len(session_history) == 0
    if is_first_message and skey not in user_names:
        user_names[skey] = "__awaiting__"
        answer_text = answer_text + "\n\nBy the way, may I know your name? I'd love to address you personally throughout our conversation."

    # Save to session history
    session_history.append({
        "user": question,
        "bot": answer_text
    })

    # Keep history small
    if len(session_history) > 10:
        session_history.pop(0)
    
    return jsonify({
        "lead_required": lead_required,
        "answer": answer_text,
        "reply": answer_text,
        "session_id": session_id
    })

# -------------------------
# Lead capture endpoint
# -------------------------
@app.route("/lead", methods=["POST"])
@limiter.limit("20/hour")
def lead():
    data = request.get_json()
    if not data:
        return jsonify({"errors": ["No data provided"]}), 400

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    session_id = data.get("session_id", "default")
    bot_id = data.get("bot_id", "self_publishing").strip()
    interested_services = data.get("interested_services", [])
    skey = scoped_key(bot_id, session_id)

    # Load brand config
    config = load_bot_config(bot_id)

    # Phase 4: Validate Widget API Key
    incoming_key = request.headers.get("X-Widget-API-Key")
    if not incoming_key or incoming_key != config.get("widget_api_key"):
        return jsonify({"error": "Unauthorized"}), 401
        
    # Phase 3: Check if tenant is suspended
    if config.get("status") != "active":
        return jsonify({"error": "This service is temporarily paused."}), 403

    # Merge server-side tracked interests
    server_interests = list(session_interests.get(skey, set()))
    all_interests = list(set(interested_services + server_interests))

    errors = []
    if not name:
        errors.append("Name is required")
    if not email and not phone:
        errors.append("Email or phone is required")

    if errors:
        return jsonify({"errors": errors}), 400

    try:
        # Get session history transcript
        session_history = chat_sessions.get(skey, [])
        transcript_text = "\n".join([f"User: {msg['user']}\nBot: {msg['bot']}" for msg in session_history])

        # LLM Lead Extraction
        extracted_services = ", ".join(all_interests)
        extracted_summary = "General Inquiry"

        if transcript_text:
            brand_name = config.get("brand_name", "our company")
            extraction_prompt = f"""You are a helpful assistant for {brand_name}.
Analyze the following conversation between a customer and our chatbot:

{transcript_text}

Identify:
1. A concise 1-2 sentence summary of the customer's project, needs, or goals.
2. The specific services they showed interest in.

You must respond ONLY in a valid JSON format with the following keys:
{{
  "summary": "1-2 sentence summary of their project/needs",
  "interested_services": "Comma-separated list of services discussed"
}}

Do not include any explanation, markdown wrappers (like ```json), or text outside of the JSON block."""
            try:
                raw_extraction = llm.invoke(extraction_prompt)
                # Parse JSON
                clean_output = raw_extraction.strip()
                if clean_output.startswith("```"):
                    clean_output = re.sub(r'^```(?:json)?\n', '', clean_output, flags=re.IGNORECASE)
                    clean_output = re.sub(r'\n```$', '', clean_output)
                    clean_output = clean_output.strip()
                
                parsed_data = json.loads(clean_output)
                extracted_summary = parsed_data.get("summary", "General Inquiry").strip()
                extracted_services = parsed_data.get("interested_services", "").strip()
                if not extracted_services:
                    extracted_services = ", ".join(all_interests)
            except Exception as e:
                print(f"[WARN] Failed to extract details via LLM: {e}. Falling back to default values.")

        # Save lead to MongoDB
        try:
            lead_document = {
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "name": name,
                "email": email,
                "phone": phone,
                "interested_services": extracted_services if extracted_services else "General Inquiry",
                "transcript": transcript_text,
                "summary": extracted_summary,
                "bot_id": bot_id
            }
            db.chats.insert_one(lead_document)
        except Exception as e:
            print(f"[ERROR] Failed to save lead to MongoDB: {e}")
        
        # Fire-and-forget to Webhook (brand-specific or global fallback)
        webhook_url = config.get("webhook_url") or os.getenv("WEBHOOK_URL")
        threading.Thread(target=send_to_webhook, args=(name, email, phone, webhook_url)).start()

        # Clear session
        if skey in session_interests:
            del session_interests[skey]
        if skey in chat_sessions:
            chat_sessions[skey].clear()
        if skey in user_names:
            del user_names[skey]

        return jsonify({
            "success": True,
            "message": "Thank you! Your information has been received.",
            "next_steps": "Our team will contact you in working hours (9am to 5 pm EST)."
        })

    except Exception as e:
        print(f"[ERROR] Failed to save lead: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"errors": ["Failed to save. Please try again."]}), 500


# DELETED: /leads/view route.
# Superseded by /admin/<bot_id>/chats, which is tenant-scoped.
# The old route read leads/lead_capture.json, a single file combining
# every tenant's leads with no bot_id filtering — unsafe to keep or "fix in place."


# -------------------------
# Admin Dashboard (Claymorphism SaaS UI)
# -------------------------

# -------------------------
# Dynamic Configuration Upload Endpoint
# -------------------------
creation_limiter_key = lambda: f"config_create:{get_remote_address()}"

@app.route("/config/upload", methods=["POST"])
@limiter.limit("10/hour")
@limiter.limit("10/hour", key_func=creation_limiter_key)
def config_upload():
    """
    Allows a brand's admin panel to upload its configuration and raw knowledge base markdown.
    Compiles the knowledge base into a FAISS index on-the-fly.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    bot_id = data.get("bot_id", "").strip()
    brand_name = data.get("brand_name", "").strip()
    brand_type = data.get("brand_type", "").strip()
    brand_facts = data.get("brand_facts", "").strip()
    system_prompt = data.get("system_prompt", "").strip() or None
    api_key = request.headers.get("X-Tenant-Api-Key", "")
    
    if not bot_id or not brand_name or not api_key:
        return jsonify({"error": "bot_id, brand_name, and X-Tenant-Api-Key header are required fields"}), 400

    if not is_valid_bot_id(bot_id):
        return jsonify({"error": "bot_id must be 3-50 characters, lowercase letters, numbers, and underscores only"}), 400

    existing = db.bot_configs.find_one({"bot_id": bot_id})
    if not existing:
        if not brand_type or brand_type not in TEMPLATES:
            return jsonify({"error": f"brand_type must be one of {list(TEMPLATES.keys())}"}), 400
    else:
        if not brand_type:
            brand_type = existing.get("brand_type", "ebook")
        elif brand_type not in TEMPLATES:
            return jsonify({"error": f"brand_type must be one of {list(TEMPLATES.keys())}"}), 400

    # Validate system prompt for format string safety ONLY if explicitly provided
    if system_prompt:
        try:
            system_prompt.format(context="", history="", question="")
        except (KeyError, IndexError, ValueError) as e:
            return jsonify({"error": f"Invalid system_prompt format: {e}. Literal braces must be doubled ({{{{ or }}}})."}), 400

    new_tenant_key = None

    if existing:
        # Must prove ownership to update
        if not existing.get("api_key_hash") or not hmac.compare_digest(hash_key(api_key), existing["api_key_hash"]):
            return jsonify({"error": "Unauthorized"}), 401
    else:
        # First-time creation: require a platform-level provisioning key
        provision_key = os.getenv("TENANT_PROVISION_KEY")
        if not provision_key or not hmac.compare_digest(api_key, provision_key):
            return jsonify({"error": "Unauthorized to create new bot_id"}), 401
        
        # A brand-new tenant must be created with a working admin password
        admin_password_check = data.get("admin_password", "").strip()
        if not admin_password_check:
            return jsonify({"error": "admin_password is required when creating a new bot_id"}), 400
        
        # Generate the tenant's real ongoing key and return it ONCE
        new_tenant_key = secrets.token_urlsafe(32)
        
    welcome_message = data.get("welcome_message", f"Hello! Welcome to {brand_name}.").strip()
    primary_color = data.get("primary_color", "#d97706").strip()
    primary_light_color = data.get("primary_light_color", "#fbbf24").strip()
    webhook_url = data.get("webhook_url", "").strip()
    
    if webhook_url:
        safe, reason = is_safe_webhook_url(webhook_url)
        if not safe:
            return jsonify({"error": f"Invalid webhook_url: {reason}"}), 400

    admin_password = data.get("admin_password", "").strip()
    knowledge_base = data.get("knowledge_base", "").strip()
    
    try:
        # Pre-compute embeddings before starting any database transaction
        texts = []
        vectors = []
        if knowledge_base:
            print(f"[INFO] Embedding knowledge base chunks for {bot_id} via API upload...")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_text(knowledge_base)
            if texts:
                vectors = embed_texts(texts)
            else:
                return jsonify({"error": "Failed to extract chunks from the knowledge base"}), 400

        update_doc = {
            "bot_id": bot_id,
            "brand_name": brand_name,
            "brand_type": brand_type,
            "brand_facts": brand_facts,
            "welcome_message": welcome_message,
            "primary_color": primary_color,
            "primary_light_color": primary_light_color,
            "webhook_url": webhook_url if webhook_url else None,
            "system_prompt": system_prompt,
            "admin_password": generate_password_hash(admin_password) if admin_password else None
        }
        if not existing and new_tenant_key:
            update_doc["api_key_hash"] = hash_key(new_tenant_key)

        try:
            with db.client.start_session() as session:
                with session.start_transaction():
                    db.bot_configs.update_one(
                        {"bot_id": bot_id},
                        {"$set": update_doc},
                        upsert=True,
                        session=session
                    )
                    
                    if texts and vectors:
                        _chunks_col.delete_many({"bot_id": bot_id}, session=session)
                        docs = [
                            {"bot_id": bot_id, "text": t, "embedding": v, "source": "upload"}
                            for t, v in zip(texts, vectors)
                        ]
                        _chunks_col.insert_many(docs, session=session)
        except Exception as tx_err:
            print(f"[WARN] Transaction failed or not supported, falling back to sequential updates: {tx_err}")
            # Fallback for standalone Mongo (which doesn't support transactions)
            db.bot_configs.update_one(
                {"bot_id": bot_id},
                {"$set": update_doc},
                upsert=True
            )
            if texts and vectors:
                store_chunks_to_mongo(bot_id, texts, vectors, source="upload")

        # Clear config cache for this bot
        if bot_id in _config_cache:
            del _config_cache[bot_id]

        response = {"success": True, "message": f"Configuration for '{bot_id}' saved and initialized successfully."}
        if not existing and new_tenant_key:
            response["tenant_api_key"] = new_tenant_key  # show once, tell them to save it
        return jsonify(response)
        
    except Exception as e:
        print(f"[ERROR] Failed to save dynamic config: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/config/rotate-key", methods=["POST"])
@limiter.limit("10/hour", key_func=creation_limiter_key)
def rotate_tenant_key():
    """
    Admin-only recovery path: issues a new tenant_api_key for an existing
    bot_id when the original key has been lost. Requires the platform
    provision key, not the tenant's own key — this IS the recovery
    mechanism for when the tenant's key is unrecoverable.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    bot_id = data.get("bot_id", "").strip()
    provision_key = request.headers.get("X-Provision-Key", "")

    if not bot_id:
        return jsonify({"error": "bot_id is required"}), 400

    expected_provision_key = os.getenv("TENANT_PROVISION_KEY")
    if not expected_provision_key or not hmac.compare_digest(provision_key, expected_provision_key):
        return jsonify({"error": "Unauthorized"}), 401

    existing = db.bot_configs.find_one({"bot_id": bot_id})
    if not existing:
        return jsonify({"error": f"No bot_id '{bot_id}' found"}), 404

    new_key = secrets.token_urlsafe(32)
    db.bot_configs.update_one(
        {"bot_id": bot_id},
        {"$set": {"api_key_hash": hash_key(new_key)}}
    )

    if bot_id in _config_cache:
        del _config_cache[bot_id]

    print(f"[SECURITY] Tenant API key rotated for bot_id='{bot_id}' by operator")

    return jsonify({
        "success": True,
        "bot_id": bot_id,
        "tenant_api_key": new_key,
        "message": "New API key issued. The previous key is now invalid. Store this key securely — it will not be shown again."
    })

# -------------------------
# Frontend Branding Config Endpoint
# -------------------------
@app.route("/config/<bot_id>", methods=["GET"])
def get_bot_config(bot_id):
    """
    Returns public configuration fields (name, colors, welcome message) 
    for the frontend widget to adjust itself dynamically.
    """
    bot_id = bot_id.strip()
    try:
        config = load_bot_config(bot_id)
        return jsonify({
            "brand_name": config.get("brand_name", bot_id.replace("_", " ").title()),
            "welcome_message": config.get("welcome_message", "Hello! How can I help you today?"),
            "primary_color": config.get("primary_color", "#d97706"),
            "primary_light_color": config.get("primary_light_color", "#fbbf24")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# -------------------------
# Claymorphism SaaS Dashboard Routes
# -------------------------
@app.route("/admin/dashboard", methods=["GET"])
@app.route("/admin", methods=["GET"])
def saas_admin_dashboard():
    """Serves the Claymorphism Super Admin Brands Overview"""
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
    """Serves the Claymorphism Add Brand Wizard"""
    return render_template("admin/add_brand.html")

@app.route("/admin/brand/<bot_id>", methods=["GET"])
@app.route("/admin/<bot_id>", methods=["GET"])
def saas_admin_brand_detail(bot_id):
    """Serves the Claymorphism Brand Detail & Config Panel"""
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
    """Serves the Claymorphism Tenant / Brand Admin Dashboard"""
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

# -------------------------
# Debug endpoints
# -------------------------
@app.route("/test-llm", methods=["GET"])
def test_llm():
    try:
        response = llm.invoke("Say hello")
        return jsonify({"status": "success", "response": response})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/clear_session", methods=["POST"])
def clear_session():
    data = request.get_json()
    session_id = data.get("session_id", "default")
    bot_id = data.get("bot_id", "self_publishing").strip()
    skey = scoped_key(bot_id, session_id)
    
    if skey in chat_sessions:
        chat_sessions[skey].clear()
    
    # Also clear the stored name so it can be captured fresh
    if skey in user_names:
        del user_names[skey]

    # Clear tracked interests
    if skey in session_interests:
        del session_interests[skey]
    
    return jsonify({"message": "Session cleared"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)

