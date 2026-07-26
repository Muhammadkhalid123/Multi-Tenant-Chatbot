# 🤖 Multi-Tenant Chatbot RAG Pipeline

A production-ready, serverless-optimized, multi-tenant Retrieval-Augmented Generation (RAG) chatbot pipeline. This application allows hosting multiple distinct chatbot assistants (tenants) simultaneously. Each tenant is configurable with its own branding (colors, welcome messages), raw knowledge base documents, and custom webhooks, complete with an interactive web widget and a secure administrative dashboard for reviewing captured leads and full chat transcripts.

---

## 🌟 Key Features

*   **👥 Dynamic Multi-Tenancy**: Run multiple independent chatbot instances simultaneously on a single deployment.
*   **⚡ Serverless-Optimized RAG**: Uses `FastEmbedEmbeddings` for offline document compilation, and a lightweight local cosine-similarity search engine matched with Hugging Face API queries at runtime, avoiding heavy model loading in serverless environments like Vercel.
*   **🎯 Intent-Driven Lead Capture**: Automatically detects user intents such as requesting quotes, scheduling consultations, or asking to speak with a human agent, and prompts the user to capture lead information.
*   **🧠 LLM-Generated Lead Summaries**: Summarizes complete user conversations into 1-2 sentence project descriptions and automatically extracts specific interested services using LLMs.
*   **📊 Secure Admin Dashboard**: Filter and review captured leads, check contact details, view extracted project summaries, and read full conversation logs.
*   **🔌 Embeddable JS Widget**: A simple floating chat bubble widget that can be easily injected onto any website using a single `<script>` tag.
*   **🔧 Dynamic Config API**: Create or update tenant configurations and upload new markdown knowledge bases dynamically.

---

## 📐 System Architecture & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as "Client Website (Widget)"
    participant API as "Flask Backend (app.py)"
    participant KB as "JSON Vector Store (Local Chunks)"
    participant HF as "Hugging Face Inference API"
    participant LLM as "LLM Provider (Groq / Ollama)"
    database DB as "MongoDB / Local JSON"

    User->>API: Send message (/ask) with bot_id & session_id
    API->>HF: Embed user query (sentence-transformers)
    HF-->>API: Query vector embedding
    API->>KB: Calculate Cosine Similarity against cached doc embeddings
    KB-->>API: Top-K matching context chunks
    API->>LLM: Invoke prompt (System Prompt + History + Context + Query)
    LLM-->>API: JSON response (reply, lead_required, extracted_name)
    API-->>User: Chatbot reply (Ask for lead details if lead_required is true)

    Note over User, API: If lead_required is true, Lead Form is shown
    User->>API: Submit contact info (/lead)
    API->>LLM: Summarize transcript & extract services
    LLM-->>API: Project summary JSON
    API->>DB: Save lead (Date, Details, Transcript, Summary, Bot ID)
    API-->>User: Success response & next steps
```

---

## 📁 Directory Structure

```text
SPC-RAG/
├── app.py                  # Main Flask server hosting API endpoints & Admin Dashboard
├── build_vector_stores.py  # Script to compile raw markdown documents into vector stores
├── requirements.txt        # Python package dependencies
├── vercel.json             # Vercel serverless configuration file
├── PROJECT_AUDIT.md        # Reference audit outlining bottlenecks & system parameters
├── config/                 # Static JSON configurations for predefined tenants
│   ├── self_publishing.json
│   └── test_brand.json
├── data/
│   └── brands/             # Raw source markdown documents grouped by bot_id
│       ├── self_publishing/
│       └── test_brand/
├── vector_stores/          # Compiled FAISS and JSON indices (pre-computed embeddings)
│   ├── self_publishing/
│   └── test_brand/
└── frontend/               # Chat frontend assets
    ├── index.html          # Main landing demo page
    ├── widget.html         # Chat widget interface (served inside an iframe)
    └── widget.js           # Floating chat bubble embed script
```

---

## 🔧 Environment Variables (`.env`)

Create a `.env` file in the root directory to configure the pipeline:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ADMIN_PASSWORD` | Flask secret key and password to access the Admin Lead Dashboard. | `admin123` |
| `MONGO_URI` | Connection URI for the MongoDB database storing lead logs and bot configurations. | `mongodb://localhost:27017/chatbot` |
| `LLM_PROVIDER` | Choose between `groq` (Cloud API) or `ollama` (Local model). | `groq` |
| `GROQ_API_KEY` | Authentication key for Groq Cloud API. (Required if provider is `groq`). | - |
| `GROQ_API_BASE` | Base API URL endpoint for Groq or OpenAI-compatible providers. | `https://api.groq.com/openai/v1` |
| `GROQ_MODEL` | Groq LLM model name. | `llama-3.3-70b-versatile` |
| `OLLAMA_BASE_URL` | Base endpoint URL for a running local Ollama instance. | `http://localhost:11434` |
| `OLLAMA_MODEL` | Name of the local LLM model installed in Ollama. | `gemma3:4b` |
| `HF_TOKEN` | Hugging Face Hub token to perform runtime query embeddings. | - |
| `WEBHOOK_URL` | Global fallback webhook URL fired when a lead is captured. | - |

---

## 🚀 Quick Start Guide

### 1. Installation
Clone the repository and set up a virtual environment:

```bash
# Clone the repository
git clone <repository_url>
cd SPC-RAG

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Prepare and Build Vector Stores
To feed knowledge documents into your chatbots:
1. Place raw markdown (`.md`) files inside `data/brands/<bot_id>/`.
2. Run the compiler script:

```bash
# Compile all brands under data/brands/
python build_vector_stores.py

# Compile a specific brand
python build_vector_stores.py self_publishing
```

This will create a `vector_stores/<bot_id>/` directory containing `index.json`, `index.faiss`, and `index.pkl` representing the chunk text and vector embeddings.

### 3. Run the Server
Launch the Flask development server:

```bash
python app.py
```
The application will start running at `http://localhost:5000`.

---

## 🔌 Integrating the Chat Widget

Add the floating chat bubble widget to any webpage by placing the following script tag in your HTML:

```html
<script 
  src="http://localhost:5000/frontend/widget.js" 
  data-bot-id="self_publishing" 
  data-api-base="http://localhost:5000">
</script>
```

### Script Attributes:
*   `src`: Points to the hosted location of `widget.js`.
*   `data-bot-id`: The target chatbot configuration to load (e.g., `self_publishing`, `test_brand`).
*   `data-api-base`: The base URL of the running backend API server.

---

## 🛰️ API Endpoint Reference

### 1. Post Question (`POST /ask`)
Sends user query to the RAG pipeline.

*   **Request Payload**:
    ```json
    {
      "question": "What editing services do you offer?",
      "session_id": "client-session-123",
      "bot_id": "self_publishing"
    }
    ```
*   **Response Payload**:
    ```json
    {
      "answer": "We offer developmental editing, proofreading, and assessment services...",
      "lead_required": false,
      "session_id": "client-session-123"
    }
    ```

### 2. Capture Lead (`POST /lead`)
Saves a lead's contact info, summarizes the chat history, and triggers configured webhooks.

*   **Request Payload**:
    ```json
    {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "+1234567890",
      "session_id": "client-session-123",
      "bot_id": "self_publishing",
      "interested_services": ["Developmental Editing", "Cover Design"]
    }
    ```
*   **Response Payload**:
    ```json
    {
      "success": true,
      "message": "Thank you! Your information has been received.",
      "next_steps": "Our team will contact you in working hours (9am to 5 pm EST)."
    }
    ```

### 3. Upload Dynamic Configuration (`POST /config/upload`)
Allows programmatically establishing a new tenant config and building its vector store dynamically.

*   **Request Payload**:
    ```json
    {
      "bot_id": "new_startup",
      "brand_name": "New Startup LLC",
      "system_prompt": "You are an assistant for New Startup LLC. Answer queries based on the context: {context}",
      "welcome_message": "Welcome to New Startup LLC Support!",
      "primary_color": "#2563eb",
      "primary_light_color": "#60a5fa",
      "webhook_url": "https://api.mycrm.com/leads",
      "knowledge_base": "# Core Services\nWe provide next-generation SaaS software solutions..."
    }
    ```

---

## 📊 Administrative Lead Dashboard

Access the built-in Lead Dashboard at `/admin` (e.g., `http://localhost:5000/admin`).
1. Log in using the password configured in `ADMIN_PASSWORD` (default: `admin123`).
2. Filter leads by specific **Chatbot ID**.
3. Click any lead entry to inspect:
   * **Full Chat Transcript**: Chronological view of every user and assistant exchange.
   * **Interested Services**: Automatically extracted product/service mentions.
   * **1-2 Sentence Project Summary**: AI-generated overview summarizing the client's needs.

---

## ☁️ Deployment on Vercel

The repository contains a `vercel.json` mapping all requests to `app.py` for Serverless deployments.

1. Install the Vercel CLI: `npm install -g vercel`
2. Run `vercel` in the project root directory.
3. Configure the environment variables (`MONGO_URI`, `GROQ_API_KEY`, `ADMIN_PASSWORD`, etc.) in the Vercel project settings dashboard.
