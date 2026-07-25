import sys
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template_string
from flask_cors import CORS
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
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

load_dotenv()

# MongoDB Database Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/chatbot")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_default_database()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("ADMIN_PASSWORD", "default-secret-key-123456")

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
# Multi-tenant Config & Vector Store Loader
# -------------------------
# Use /tmp for caching on Vercel since the default user home directory is read-only
cache_dir = "/tmp/fastembed_cache" if os.environ.get("VERCEL") == "1" else None
embeddings = FastEmbedEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_dir=cache_dir
)

# Cache in-memory loaded retrievers and brand configurations
_retrievers_cache = {}
_config_cache = {}

def load_bot_config(bot_id):
    """Load configuration for a specific chatbot brand"""
    if bot_id in _config_cache:
        return _config_cache[bot_id]
        
    # 1. Try to load from database first
    try:
        row = db.bot_configs.find_one({"bot_id": bot_id})
        if row:
            # Remove MongoDB internal ObjectId
            row.pop("_id", None)
            _config_cache[bot_id] = row
            return row
    except Exception as e:
        print(f"[ERROR] Failed to load config from database for {bot_id}: {e}")
        
    # 2. Fall back to configuration file config/<bot_id>.json
    config_path = os.path.join("config", f"{bot_id}.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                _config_cache[bot_id] = config
                return config
        except Exception as e:
            print(f"[ERROR] Failed to load config file for {bot_id}: {e}")
            
    # 3. Fall back to default config values
    default_config = {
        "bot_id": bot_id,
        "brand_name": bot_id.replace("_", " ").title(),
        "welcome_message": f"Hello! Welcome to {bot_id.replace('_', ' ').title()} Chat Assistant. How can I help you today?",
        "primary_color": "#d97706",
        "primary_light_color": "#fbbf24",
        "webhook_url": None,
        "system_prompt": "You are a helpful assistant. Answer the user's questions clearly and concisely.\n\nContext: {context}\n\nPrevious conversation: {history}\n\nQuestion: {question}\n\nJSON Response:"
    }
    return default_config

def get_retriever(bot_id):
    """Retrieve the FAISS vector store retriever for a specific bot_id"""
    if bot_id in _retrievers_cache:
        return _retrievers_cache[bot_id]
        
    # Check /tmp first if running on Vercel
    base_dir = "/tmp" if os.environ.get("VERCEL") == "1" else "."
    vector_store_path = os.path.join(base_dir, "vector_stores", bot_id)
    
    if not os.path.exists(vector_store_path):
        # Fall back to packaged read-only directory
        vector_store_path = os.path.join("vector_stores", bot_id)
        
    if os.path.exists(vector_store_path):
        print(f"[INFO] Loading vector store for {bot_id}...")
        vectorstore = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        _retrievers_cache[bot_id] = retriever
        return retriever
    else:
        print(f"[WARN] No vector store found at {vector_store_path}. Returning None.")
        return None

# -------------------------
# LLM setup - Support Ollama and Groq (OpenAI-compatible)
# -------------------------
llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()

if llm_provider == "groq":
    print("[INFO] Initializing ChatOpenAI client for Groq...")
    llm = ChatOpenAI(
        openai_api_base=os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1"),
        openai_api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
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



def extract_interests_from_message(question):
    """
    Extract mentioned services/packages from a user message to track their interests.
    Returns a set of interest strings.
    """
    interests = set()
    q_lower = question.lower()

    service_keywords = {
        "Manuscript Assessment": ["manuscript assessment", "assess my manuscript", "manuscript review"],
        "Developmental Editing": ["developmental editing", "developmental edit", "editing"],
        "Cover Design": ["cover design", "book cover", "cover"],
        "Interior Formatting": ["formatting", "interior format", "kdp format", "ebook format"],
        "Global Distribution": ["distribution", "global distribution", "distribute"],
        "Book Marketing": ["marketing", "book marketing", "launch strategy", "advertis"],
        "Royalty Accounting": ["royalty", "royalties", "royalty tracking", "royalty accounting"],
        "Ghostwriting": ["ghostwriting", "ghost writing", "ghostwrite"],
        "Copyright Registration": ["copyright", "copyright registration", "rights protection"],
        "Metadata & SEO": ["metadata", "seo", "discoverability"],
        "Audiobook Production": ["audiobook", "audio book", "audio production"],
        "Video Trailer": ["video trailer", "book trailer"],
        "Proofreading": ["proofreading", "proofread", "copyediting"],
    }

    for service, keywords in service_keywords.items():
        if any(kw in q_lower for kw in keywords):
            interests.add(service)

    return interests

# -------------------------
# Webhook Helper
# -------------------------
def send_to_webhook(name, email, phone, webhook_url):
    if not webhook_url:
        return
        
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "form_type": "Contact Form",
        "name": name,
        "email": email,
        "phone": phone
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=5)
        print("[INFO] Successfully sent lead to Webhook.")
    except Exception as e:
        print(f"[ERROR] Failed to send lead to Webhook: {e}")

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return send_from_directory('frontend', 'index.html')

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

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    session_id = data.get("session_id", "default")
    bot_id = data.get("bot_id", "self_publishing").strip()
    
    if not question:
        return jsonify({"error": "No message provided"}), 400

    # Load brand config and retriever
    config = load_bot_config(bot_id)
    retriever = get_retriever(bot_id)

    # Track service interests from this message
    new_interests = extract_interests_from_message(question)
    session_interests[session_id].update(new_interests)

    # Get session history
    session_history = chat_sessions[session_id]
    
    # Simple history text (last 3 exchanges only)
    history_text = "\n".join([f"User: {msg['user']}\nBot: {msg['bot']}" 
                              for msg in session_history[-3:]])
    
    # Get context from the bot's specific retriever
    context = ""
    if retriever:
        try:
            docs = retriever.invoke(question)
            context = "\n\n".join([doc.page_content for doc in docs])
            context = context[:4000]  # Limit context size
        except Exception as e:
            print(f"[ERROR] Retrieval failed for {bot_id}: {e}")
    
    # Inject the user's known name into the history context
    known_name = user_names.get(session_id, "")
    name_context = f"The user's name is {known_name}. Use their name naturally in your replies.\n" if known_name and known_name != "__awaiting__" else ""

    # Build prompt dynamically using config prompt template
    prompt_template = PromptTemplate(
        input_variables=["context", "history", "question"],
        template=config.get("system_prompt")
    )
    prompt = prompt_template.format(
        context=name_context + context,
        history=history_text,
        question=question
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
        
        is_awaiting_name = session_id in user_names and user_names[session_id] == "__awaiting__"
        if extracted_name:
            user_names[session_id] = extracted_name
        elif is_awaiting_name:
            user_names[session_id] = ""
        
    except Exception as e:
        print(f"[ERROR] LLM Invocation failed: {e}")
        import traceback
        traceback.print_exc()
        answer_text = f"I'm here to help with your {config.get('brand_name')} questions. How can I help you?"
        lead_required = False
    
    # After very first exchange: ask for user's name
    is_first_message = len(session_history) == 0
    if is_first_message and session_id not in user_names:
        user_names[session_id] = "__awaiting__"
        answer_text = answer_text + "\n\nBy the way, may I know your name? I'd love to address you personally throughout our conversation."

    # Save to session history
    session_history.append({
        "user": question,
        "bot": answer_text
    })

    # Keep history small
    if len(session_history) > 10:
        session_history.pop(0)
    
    # Introduce 3 seconds delay in replying
    import time
    time.sleep(3)
    
    return jsonify({
        "lead_required": lead_required,
        "answer": answer_text,
        "session_id": session_id
    })

# -------------------------
# Lead capture endpoint
# -------------------------
@app.route("/lead", methods=["POST"])
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

    # Load brand config
    config = load_bot_config(bot_id)

    # Merge server-side tracked interests
    server_interests = list(session_interests.get(session_id, set()))
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
        session_history = chat_sessions.get(session_id, [])
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

        # Save lead to JSON file (backup)
        lead_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "interested_services": extracted_services if extracted_services else "General Inquiry",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "summary": extracted_summary,
            "transcript": transcript_text,
            "bot_id": bot_id
        }
        save_lead_to_json(lead_data)
        
        # Fire-and-forget to Webhook (brand-specific or global fallback)
        webhook_url = config.get("webhook_url") or os.getenv("WEBHOOK_URL")
        threading.Thread(target=send_to_webhook, args=(name, email, phone, webhook_url)).start()

        # Clear session
        if session_id in session_interests:
            del session_interests[session_id]
        if session_id in chat_sessions:
            chat_sessions[session_id].clear()
        if session_id in user_names:
            del user_names[session_id]

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


def save_lead_to_json(lead_data):
    """Save lead data to JSON file"""
    LEADS_DIR = "/tmp/leads" if os.environ.get("VERCEL") == "1" else "leads"
    LEADS_JSON = os.path.join(LEADS_DIR, "lead_capture.json")
    os.makedirs(LEADS_DIR, exist_ok=True)
    try:
        existing_data = []
        if os.path.exists(LEADS_JSON):
            with open(LEADS_JSON, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    existing_data = json.loads(content)
        
        existing_data.append(lead_data)
        
        with open(LEADS_JSON, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write lead to json: {e}")
        raise


# -------------------------
# Sales team: View leads (JSON backup)
# -------------------------
@app.route("/leads/view", methods=["GET"])
def view_leads():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    LEADS_DIR = "/tmp/leads" if os.environ.get("VERCEL") == "1" else "leads"
    LEADS_JSON = os.path.join(LEADS_DIR, "lead_capture.json")
    if not os.path.exists(LEADS_JSON):
        return jsonify({"leads": [], "total": 0})
    
    try:
        with open(LEADS_JSON, "r", encoding="utf-8") as f:
            content = f.read()
            leads = json.loads(content) if content else []
        return jsonify({"leads": leads, "total": len(leads)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# Admin Dashboard HTML Templates
# -------------------------
ADMIN_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - Self Publishing Consultant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-page: #0b0f19;
            --bg-surface: rgba(15, 23, 42, 0.7);
            --bg-card: rgba(30, 41, 59, 0.4);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(217, 119, 6, 0.3);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #d97706;
            --primary-light: #fbbf24;
            --error: #ef4444;
            --font-serif: 'Lora', serif;
            --font-sans: 'Plus Jakarta Sans', sans-serif;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-sans);
            background: radial-gradient(circle at top right, #1e1b4b, var(--bg-page) 65%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .card {
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            text-align: center;
        }
        h1 { font-family: var(--font-serif); font-size: 22px; color: var(--primary-light); margin-bottom: 8px; }
        p { font-size: 13px; color: var(--text-muted); margin-bottom: 24px; }
        .input-group { margin-bottom: 20px; text-align: left; }
        label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600; }
        input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-main);
            font-size: 14px;
            outline: none;
            transition: var(--transition);
        }
        input:focus { border-color: var(--primary); box-shadow: 0 0 10px rgba(217, 119, 6, 0.15); }
        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, var(--primary) 0%, #b45309 100%);
            border: none;
            color: white;
            font-weight: 600;
            font-size: 14px;
            border-radius: 10px;
            cursor: pointer;
            transition: var(--transition);
            margin-top: 10px;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3); }
        .error-msg { color: var(--error); font-size: 12px; margin-top: 12px; line-height: 1.4; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Dashboard Login</h1>
        <p>Access the Self Publishing Consultant Lead Portal</p>
        <form method="POST">
            <div class="input-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter administrative password" required autofocus>
            </div>
            <button type="submit" class="btn">Authenticate</button>
            {% if error %}
            <div class="error-msg">{{ error }}</div>
            {% endif %}
        </form>
    </div>
</body>
</html>"""

ADMIN_CHATS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Dashboard - Self Publishing Consultant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-page: #0b0f19;
            --bg-surface: rgba(15, 23, 42, 0.7);
            --bg-sidebar: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.4);
            --bg-card-hover: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(217, 119, 6, 0.3);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #d97706;
            --primary-light: #fbbf24;
            --font-serif: 'Lora', serif;
            --font-sans: 'Plus Jakarta Sans', sans-serif;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-sans);
            background: radial-gradient(circle at top right, #1e1b4b, var(--bg-page) 65%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            overflow: hidden;
        }
        header {
            padding: 24px 40px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.4);
        }
        h1 { font-family: var(--font-serif); font-size: 24px; color: var(--primary-light); }
        .logout-btn {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: var(--transition);
        }
        .logout-btn:hover { border-color: var(--primary); color: var(--primary-light); background: rgba(217, 119, 6, 0.1); }
        .table-container { padding: 30px; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-muted);
            padding: 12px 18px;
            border-bottom: 1px solid var(--border);
            font-weight: 700;
        }
        td { padding: 18px; border-bottom: 1px solid var(--border); font-size: 13.5px; vertical-align: top; }
        tr:hover td { background: rgba(255,255,255,0.015); }
        .chat-row { cursor: pointer; transition: var(--transition); }
        .chat-row:hover { background: var(--bg-card-hover); }
        .name { font-weight: 600; color: var(--text-main); }
        .contact { font-size: 12.5px; color: var(--text-muted); line-height: 1.4; }
        .services { display: flex; flex-wrap: wrap; gap: 4px; }
        .badge {
            background: rgba(217,119,6,0.1);
            border: 1px solid rgba(217,119,6,0.25);
            color: var(--primary-light);
            border-radius: 12px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
        }
        .summary { color: var(--text-muted); font-size: 13px; max-width: 320px; line-height: 1.4; }
        .date { color: var(--text-muted); font-size: 12.5px; white-space: nowrap; }
        .action-link {
            color: var(--primary-light);
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: var(--transition);
        }
        .action-link:hover { color: var(--primary); text-decoration: underline; }
        .no-leads { text-align: center; padding: 60px; color: var(--text-muted); font-size: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Lead Dashboard — Multi-Tenant</h1>
            <a href="/admin/logout" class="logout-btn">Log Out</a>
        </header>
        <div style="padding: 20px 30px 0 30px; display: flex; align-items: center; gap: 10px;">
            <form method="GET" action="/admin/chats" style="display: flex; align-items: center; gap: 10px;">
                <label for="bot_id_select" style="display: inline; text-transform: none; font-size: 13.5px; font-weight: normal; color: var(--text-main);">Filter by Chatbot:</label>
                <select id="bot_id_select" name="bot_id" onchange="this.form.submit()" style="padding: 6px 12px; background: rgba(15, 23, 42, 0.8); border: 1px solid var(--border); border-radius: 6px; color: var(--text-main); font-size: 13px; outline: none; cursor: pointer;">
                    <option value="">-- All Chatbots --</option>
                    {% for b in all_bots %}
                        <option value="{{ b }}" {% if b == selected_bot_id %}selected{% endif %}>{{ b }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>
        <div class="table-container">
            {% if chats %}
            <table>
                <thead>
                    <tr>
                        <th>Date & Time</th>
                        <th>Chatbot ID</th>
                        <th>Author Name</th>
                        <th>Contact Details</th>
                        <th>Requested Services</th>
                        <th>Project Summary</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for chat in chats %}
                    <tr class="chat-row" onclick="window.location.href='/admin/chats/{{ chat.id }}'">
                        <td class="date">{{ chat.started_at }}</td>
                        <td style="color: var(--primary-light); font-weight: 600;">{{ chat.bot_id if chat.bot_id else 'General' }}</td>
                        <td class="name">{{ chat.name }}</td>
                        <td class="contact">
                            <div>📧 {{ chat.email }}</div>
                            {% if chat.phone %}<div>📞 {{ chat.phone }}</div>{% endif %}
                        </td>
                        <td class="services">
                            {% if chat.interested_services %}
                                {% for svc in chat.interested_services.split(',') %}
                                    <span class="badge">{{ svc.strip() }}</span>
                                {% endfor %}
                            {% else %}
                                <span class="badge" style="background:rgba(255,255,255,0.05);border-color:transparent;color:var(--text-muted);">General</span>
                            {% endif %}
                        </td>
                        <td class="summary">{{ chat.summary }}</td>
                        <td><a href="/admin/chats/{{ chat.id }}" class="action-link">View Details →</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="no-leads">No leads captured yet. Keep testing!</div>
            {% endif %}
        </div>
    </div>
</body>
</html>"""

ADMIN_DETAIL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Details - Self Publishing Consultant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-page: #0b0f19;
            --bg-surface: rgba(15, 23, 42, 0.7);
            --bg-sidebar: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.4);
            --bg-card-hover: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(217, 119, 6, 0.3);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #d97706;
            --primary-light: #fbbf24;
            --font-serif: 'Lora', serif;
            --font-sans: 'Plus Jakarta Sans', sans-serif;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-sans);
            background: radial-gradient(circle at top right, #1e1b4b, var(--bg-page) 65%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .back-link {
            color: var(--text-muted);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 24px;
            transition: var(--transition);
        }
        .back-link:hover { color: var(--primary-light); }
        .grid {
            display: grid;
            grid-template-columns: 420px 1fr;
            gap: 30px;
        }
        .card {
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .card h2 { font-family: var(--font-serif); font-size: 22px; color: var(--primary-light); border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .field { display: flex; flex-direction: column; gap: 4px; }
        .field-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); font-weight: 700; }
        .field-value { font-size: 14px; color: var(--text-main); line-height: 1.4; }
        .services { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
        .badge {
            background: rgba(217,119,6,0.1);
            border: 1px solid rgba(217,119,6,0.25);
            color: var(--primary-light);
            border-radius: 12px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
        }
        .chat-feed {
            background: var(--bg-surface);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-height: 700px;
            overflow-y: auto;
        }
        .chat-feed h2 { font-family: var(--font-serif); font-size: 20px; color: var(--primary-light); margin-bottom: 10px; }
        .message { display: flex; flex-direction: column; gap: 6px; max-width: 80%; padding: 12px 16px; border-radius: 14px; font-size: 13.5px; line-height: 1.5; }
        .message.user {
            align-self: flex-end;
            background: linear-gradient(135deg, var(--primary) 0%, #b45309 100%);
            color: white;
            border-bottom-right-radius: 2px;
        }
        .message.bot {
            align-self: flex-start;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            color: var(--text-main);
            border-bottom-left-radius: 2px;
        }
        .message-sender { font-size: 10px; font-weight: 700; text-transform: uppercase; opacity: 0.8; letter-spacing: 0.5px; }
        .message-text { word-wrap: break-word; }
        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin/chats" class="back-link">← Back to Lead Dashboard</a>
        <div class="grid">
            <!-- Left Panel: Extracted Details -->
            <div class="card">
                <h2>Lead Details</h2>
                <div class="field">
                    <div class="field-label">Date Captured</div>
                    <div class="field-value">{{ chat.started_at }}</div>
                </div>
                <div class="field">
                    <div class="field-label">Chatbot Brand ID</div>
                    <div class="field-value" style="color: var(--primary-light); font-weight:600;">{{ chat.bot_id if chat.bot_id else 'General' }}</div>
                </div>
                <div class="field">
                    <div class="field-label">Author Name</div>
                    <div class="field-value" style="font-size: 16px; font-weight:600; color: var(--primary-light);">{{ chat.name }}</div>
                </div>
                <div class="field">
                    <div class="field-label">Email Address</div>
                    <div class="field-value">{{ chat.email }}</div>
                </div>
                {% if chat.phone %}
                <div class="field">
                    <div class="field-label">Phone Number</div>
                    <div class="field-value">{{ chat.phone }}</div>
                </div>
                {% endif %}
                <div class="field">
                    <div class="field-label">Interested Services</div>
                    <div class="services">
                        {% if chat.interested_services %}
                            {% for svc in chat.interested_services.split(',') %}
                                <span class="badge">{{ svc.strip() }}</span>
                            {% endfor %}
                        {% else %}
                            <span class="badge" style="background:rgba(255,255,255,0.05);border-color:transparent;color:var(--text-muted);">General</span>
                        {% endif %}
                    </div>
                </div>
                <div class="field">
                    <div class="field-label">Project Summary</div>
                    <div class="field-value" style="font-style: italic; color: var(--text-muted); border-left: 2px solid var(--primary); padding-left: 10px;">{{ chat.summary }}</div>
                </div>
            </div>

            <!-- Right Panel: Full Conversation Transcript -->
            <div class="chat-feed">
                <h2>Conversation Transcript</h2>
                {% if transcript_list %}
                    {% for msg in transcript_list %}
                        {% if msg.sender.lower() == 'user' %}
                            <div class="message user">
                                <div class="message-sender">Author</div>
                                <div class="message-text">{{ msg.text }}</div>
                            </div>
                        {% else %}
                            <div class="message bot">
                                <div class="message-sender">Assistant</div>
                                <div class="message-text">{{ msg.text }}</div>
                            </div>
                        {% endif %}
                    {% endfor %}
                {% else %}
                    <div style="color:var(--text-muted); font-size: 14px;">No conversation logs found.</div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>"""


# -------------------------
# Dynamic Configuration Upload Endpoint
# -------------------------
@app.route("/config/upload", methods=["POST"])
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
    system_prompt = data.get("system_prompt", "").strip()
    
    if not bot_id or not brand_name or not system_prompt:
        return jsonify({"error": "bot_id, brand_name, and system_prompt are required fields"}), 400
        
    welcome_message = data.get("welcome_message", f"Hello! Welcome to {brand_name}.").strip()
    primary_color = data.get("primary_color", "#d97706").strip()
    primary_light_color = data.get("primary_light_color", "#fbbf24").strip()
    webhook_url = data.get("webhook_url", "").strip()
    admin_password = data.get("admin_password", "").strip()
    knowledge_base = data.get("knowledge_base", "").strip()
    
    try:
        # Save or update in MongoDB
        db.bot_configs.update_one(
            {"bot_id": bot_id},
            {"$set": {
                "bot_id": bot_id,
                "brand_name": brand_name,
                "welcome_message": welcome_message,
                "primary_color": primary_color,
                "primary_light_color": primary_light_color,
                "webhook_url": webhook_url if webhook_url else None,
                "system_prompt": system_prompt,
                "admin_password": admin_password if admin_password else None
            }},
            upsert=True
        )
        
        # Clear config cache for this bot
        if bot_id in _config_cache:
            del _config_cache[bot_id]
            
        # Compile vector store if knowledge base is provided
        if knowledge_base:
            print(f"[INFO] Compiling vector store for {bot_id} via API upload...")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_text(knowledge_base)
            
            if texts:
                vectorstore = FAISS.from_texts(texts, embeddings)
                base_dir = "/tmp" if os.environ.get("VERCEL") == "1" else "."
                vector_store_path = os.path.join(base_dir, "vector_stores", bot_id)
                os.makedirs(vector_store_path, exist_ok=True)
                vectorstore.save_local(vector_store_path)
                
                # Invalidate retrievers cache to force reload on next chat
                if bot_id in _retrievers_cache:
                    del _retrievers_cache[bot_id]
                print(f"[OK] Vector store compiled successfully via API for '{bot_id}'")
            else:
                return jsonify({"error": "Failed to extract chunks from the knowledge base"}), 400
                
        return jsonify({"success": True, "message": f"Configuration for '{bot_id}' saved and initialized successfully."})
        
    except Exception as e:
        print(f"[ERROR] Failed to save dynamic config: {e}")
        return jsonify({"error": str(e)}), 500

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
# Admin Portal Routes
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password")
        if password == os.getenv("ADMIN_PASSWORD", "admin123"):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_chats"))
        else:
            error = "Invalid administrative password"
    return render_template_string(ADMIN_LOGIN_HTML, error=error)

@app.route("/admin/chats", methods=["GET"])
def admin_chats():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
        
    selected_bot_id = request.args.get("bot_id", "").strip()
    try:
        # Get all distinct bot_ids from database for filtering
        db_bots = db.chats.distinct("bot_id")
        db_bots = [b for b in db_bots if b]
        
        # Get bot ids from bot_configs table
        db_config_bots = db.bot_configs.distinct("bot_id")
        
        # Also scan the config directory for available bot configs
        config_bots = []
        if os.path.exists("config"):
            config_bots = [f[:-5] for f in os.listdir("config") if f.endswith(".json")]
            
        all_bots = sorted(list(set(db_bots + db_config_bots + config_bots)))
        
        # Query chats from MongoDB
        query = {"bot_id": selected_bot_id} if selected_bot_id else {}
        chats_cursor = db.chats.find(query).sort("started_at", -1)
        
        chats = []
        for chat in chats_cursor:
            # Map MongoDB ObjectId to 'id' string so HTML template works seamlessly
            chat["id"] = str(chat["_id"])
            chats.append(chat)
            
    except Exception as e:
        print(f"[ERROR] Failed to query leads: {e}")
        chats = []
        all_bots = []
        
    return render_template_string(ADMIN_CHATS_HTML, chats=chats, all_bots=all_bots, selected_bot_id=selected_bot_id)

@app.route("/admin/chats/<chat_id>", methods=["GET"])
def admin_chat_detail(chat_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    try:
        chat = db.chats.find_one({"_id": ObjectId(chat_id)})
        
        if not chat:
            return "Chat not found", 404
            
        chat["id"] = str(chat["_id"])
        
        transcript_list = []
        raw_transcript = chat.get("transcript", "")
        if raw_transcript:
            lines = raw_transcript.split('\n')
            for line in lines:
                if line.startswith("User: "):
                    transcript_list.append({"sender": "User", "text": line[6:]})
                elif line.startswith("Bot: "):
                    transcript_list.append({"sender": "Bot", "text": line[5:]})
    except Exception as e:
        print(f"[ERROR] Failed to fetch lead detail: {e}")
        return "Internal server error", 500
        
    return render_template_string(ADMIN_DETAIL_HTML, chat=chat, transcript_list=transcript_list)

@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

# -------------------------
# Widget Route
# -------------------------
@app.route("/widget", methods=["GET"])
def widget():
    """
    Serves the minimal chat-only interface for embedding in standard iFrames.
    """
    return send_from_directory('frontend', 'widget.html')

@app.route("/frontend/<path:filename>", methods=["GET"])
def serve_frontend(filename):
    """
    Serves static frontend assets (like widget.js).
    """
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
    
    if session_id in chat_sessions:
        chat_sessions[session_id].clear()
    
    # Also clear the stored name so it can be captured fresh
    if session_id in user_names:
        del user_names[session_id]

    # Clear tracked interests
    if session_id in session_interests:
        del session_interests[session_id]
    
    return jsonify({"message": "Session cleared"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)

