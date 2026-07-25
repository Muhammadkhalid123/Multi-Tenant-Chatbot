print("1. Importing core libraries...")
import sys
import os
import glob
import re
import json
import sqlite3
import threading
from datetime import datetime
from collections import defaultdict

print("2. Importing Flask and CORS...")
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template_string
from flask_cors import CORS

print("3. Importing Langchain Community components...")
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

print("4. Importing remaining Langchain components...")
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

print("5. Loading environment...")
from dotenv import load_dotenv
load_dotenv()

print("6. Initializing Flask app...")
app = Flask(__name__)
CORS(app)

print("7. Initializing SQLite db...")
DB_PATH = "leads.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        interested_services TEXT,
        transcript TEXT,
        summary TEXT
    )
""")
conn.commit()
conn.close()
print("   DB initialized.")

print("8. Initializing FastEmbedEmbeddings...")
embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
print("   Embeddings initialized.")

print("9. Loading local FAISS index...")
VECTOR_STORE_PATH = "vector_store/self_publishing_consultant_faiss_index"
if os.path.exists(VECTOR_STORE_PATH):
    print("   Index directory exists. Loading local FAISS store...")
    vectorstore = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
    print("   FAISS index loaded.")
else:
    print("   Index directory does not exist.")

print("10. Setting up LLM...")
llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()
print(f"   LLM Provider: {llm_provider}")
if llm_provider == "groq":
    llm = ChatOpenAI(
        openai_api_base=os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1"),
        openai_api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.7
    )
print("    LLM setup completed.")

print("Diagnostic script finished successfully!")
