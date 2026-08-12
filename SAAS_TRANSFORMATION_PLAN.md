# SaaS Transformation Plan: SPC-RAG Multi-Tenant Architecture

## Step 1: Current State Audit & Bottlenecks

### Current State Summary
- **`app.py`**: Handles all routing. Tenant identity (`bot_id`) is resolved via request JSON payload in `/ask` and `/lead`, or via query parameters. Auth is a mix of global `.env` (`ADMIN_PASSWORD`) and per-tenant config (`admin_username`/`admin_password` seen in `tecwrites.json`). 
- **`build_vector_stores.py`**: Reads markdown files from local disk (`data/brands/<bot_id>/*.md`) and embeds them, pushing them to a shared MongoDB `chunks` collection.
- **`config/*.json`**: Currently stores basic UI branding, prompts, and some admin credentials.
- **`PROJECT_AUDIT.md`**: Not present in the current repository.
- **`frontend/widget.js` & `widget.html`**: The widget extracts `bot_id` from the script tag's data attributes or URL parameters and passes it along to the iframe and API calls.
- **`.env` variables**: Contains a mix of global infrastructure settings (`MONGO_URI`, `LLM_PROVIDER`) and legacy single-tenant settings (`ADMIN_PASSWORD`, global `WEBHOOK_URL`, `username`/`pass`).

### Multi-Tenant & Security Vulnerabilities (What Will Break/Leak)
1. **Unauthenticated Widget Embeds**: The widget relies purely on `bot_id` to route requests. Anyone can inspect the network tab, find a paying customer's `bot_id`, and embed that chatbot on their own site, burning your LLM API costs.
2. **Global Fallbacks**: The `/lead` route falls back to a global `os.getenv("WEBHOOK_URL")` if a tenant doesn't have one. This could accidentally route one tenant's leads to your master webhook.
3. **Data Isolation**: All embeddings live in a single `chunks` collection and leads live in a single `chats` collection. Isolation relies entirely on `$eq: bot_id` filters in queries. While functional, a single dropped `bot_id` filter in a future admin route will cause catastrophic data leakage between clients.
4. **Local Disk Dependency**: `build_vector_stores.py` relies on `data/brands/<bot_id>/*.md` on the local disk. In a distributed SaaS environment, local disk storage won't scale across multiple servers/containers.
5. **Config Source of Truth**: The app attempts to load from MongoDB `bot_configs` first, then falls back to local `config/<bot_id>.json`. This split-brain configuration is dangerous for a SaaS.

## Step 2: Two-Tier Admin Model

To support you as the SaaS operator and your clients as Brand Admins, we need strict server-side role separation.

### Proposed Auth Model: Role-Based Sessions (or JWT)
- **Super Admin (You)**: Authenticated against a secure set of credentials (either in a `.env` like `SUPER_ADMIN_USER`/`PASS` or a dedicated `super_admins` DB collection). 
  - Token/Session Claim: `{ "role": "super_admin", "bot_id": "*" }`
- **Brand Admin (Your Customer)**: Authenticated against credentials stored in their specific `bot_configs` document.
  - Token/Session Claim: `{ "role": "brand_admin", "bot_id": "tecwrites" }`

### Enforcement & Schema Changes
- **Server-Side Verification**: Do not rely on hiding UI elements. Create Flask decorators (e.g., `@require_super_admin`, `@require_brand_admin(bot_id)`) that inspect the session/JWT on *every* API request.
- **Session Handling**: If using Flask `session`, ensure `SESSION_COOKIE_SECURE=True` and `SESSION_COOKIE_HTTPONLY=True`.

## Step 3: Extended Tenant Data Model

Move all tenant configuration out of local `.json` files and strictly into the MongoDB `bot_configs` (or a new `tenants`) collection.

### Updated Schema (MongoDB `tenants` or `bot_configs` collection)
```json
{
  "_id": "ObjectId",
  "bot_id": "unique_brand_identifier",
  "brand_name": "Brand Name",
  "status": "active", // pending | active | suspended | cancelled
  "plan_tier": "pro_monthly",
  "billing_cycle": "monthly",
  "owner_email": "client@brand.com",
  "owner_contact": "+1234567890",
  "created_at": "ISODate",
  "suspended_at": null,
  "suspended_reason": null,
  
  // Security
  "widget_api_key": "sk_live_...", // Required to authorize /ask and /lead requests
  "allowed_domains": ["brand.com", "www.brand.com"], // CORS/Referer validation
  
  // Usage tracking
  "usage": {
    "messages_current_cycle": 1450,
    "leads_current_cycle": 42,
    "cycle_start_date": "ISODate"
  },
  
  // Customization (existing)
  "primary_color": "#0d9488",
  "welcome_message": "...",
  "system_prompt": "...",
  "webhook_url": "..."
}
```

## Step 4: Tenant Lifecycle Workflows

### 1. Add Brand
- **Action**: Super Admin submits a "New Brand" form.
- **System**: 
  - Creates a new MongoDB document with `status = active` and generates a secure `widget_api_key`.
  - Provisions a cloud storage bucket path (e.g., AWS S3 or GridFS) for their markdown files instead of local disk.
  - Generates the widget embed snippet containing the `widget_api_key`.
- **Customer**: Receives a welcome email with their Dashboard login link and embed snippet.

### 2. Suspend Brand (Non-payment or manual)
- **Action**: Stripe webhook fires for failed payment, or Super Admin clicks "Suspend".
- **System**: Updates `status = suspended`, sets `suspended_at` and `suspended_reason`.
- **Widget Experience**: The `/ask` endpoint checks status. If suspended, it immediately returns a fixed JSON response (e.g., "This service is temporarily paused.") without hitting the LLM provider, saving you API costs.
- **Dashboard Experience**: Brand Admin can log in, but the dashboard is locked in a "Read-Only / Payment Required" state. They cannot edit configs or view new leads until resolved.

### 3. Reactivate Brand
- **Action**: Super Admin clicks "Reactivate" or Stripe sends `invoice.paid`.
- **System**: Updates `status = active`, clears `suspended_at`. 
- **System**: No vector store rebuild is strictly necessary unless data was wiped, but cache invalidation for the config is required.

### 4. Remove/Delete Brand
- **Action**: Super Admin initiates deletion.
- **System (Soft Delete by Default)**: Updates `status = cancelled`. The bot goes offline. Data remains in the DB for 30 days for compliance/reactivation.
- **System (Hard Delete)**: A separate "Purge Data" action deletes all records in `chunks`, `chats`, and `bot_configs` matching the `bot_id`, and deletes cloud storage files.

### 5. Billing Integration
- **Flow**: Use Stripe Checkout for subscriptions. Stripe sends webhooks (`customer.subscription.deleted`, `invoice.payment_failed`) to a new `/api/webhooks/stripe` endpoint.
- **Logic**: The webhook looks up the tenant by a stored `stripe_customer_id` and automatically toggles the `status` field.

## Step 5: Required Screens & UI Map

### Super Admin Dashboard (You)
- **Brands Overview**: Data table listing all tenants. Columns: Brand Name, Status (Badge), Plan Tier, MRR, Messages This Month, Leads This Month. Quick actions: View, Suspend.
- **Add Brand Wizard**: 
  - Step 1: Basic Info (bot_id, owner email).
  - Step 2: Branding (colors, welcome message).
  - Step 3: Knowledge Base (upload files).
- **Brand Detail (God Mode)**: Full configuration editor, danger zone (Suspend/Purge), API Key rotation, raw usage metrics, and lead viewer for that specific brand.
- **Global Leads**: A cross-tenant table of all leads generated across the platform (useful for aggregate reporting).
- **Settings**: Global LLM provider keys, global Stripe webhook secrets, Super Admin password rotation.

### Brand Admin Dashboard (Your Customer)
- **Overview**: High-level stats: Total Conversations, Total Leads captured this month.
- **Leads Manager**: Table of their own leads only, with export to CSV functionality.
- **Knowledge Base**: Interface to upload new Markdown/PDF files and click "Retrain Bot".
- **Customization**: Form to update colors, welcome message, and their specific Zapier/Google Sheets webhook URL.
- **Installation**: Copy-pasteable embed snippet with their specific `bot_id` and `api_key`.
- **Billing**: (Optional) Link to Stripe Customer Portal to update credit card.

## Step 6: API Surface Gap Analysis

### Existing Endpoints to Modify
- `POST /ask` & `POST /lead`: 
  - Must validate the new `widget_api_key` against the `bot_id`.
  - Must check if `tenant.status == 'active'` before proceeding.
  - Must increment `usage_counters`.

### New Endpoints Required
- `POST /api/admin/auth/login`: Needs to handle both Super Admin and Brand Admin logins and issue the correct session/JWT.
- `GET /api/admin/brands`: (Super Admin only) List all tenants.
- `POST /api/admin/brands`: (Super Admin only) Create a new tenant.
- `GET /api/admin/brands/:id`: Get tenant details (Super Admin can view any; Brand Admin can only view their own).
- `PATCH /api/admin/brands/:id`: Update config/status.
- `POST /api/admin/brands/:id/knowledge`: Upload new knowledge files and trigger a vector store rebuild.
- `GET /api/admin/brands/:id/leads`: Fetch leads, strictly isolated by `bot_id`.

## Step 7: Open Questions for Product Decisions

> [!IMPORTANT]
> Before we begin coding, I need your direction on the following business logic:

1. **Widget Security**: Are you okay with introducing a `widget_api_key`? This means updating the `widget.js` script to require it. We should also enforce `allowed_domains` so a stolen API key can't be used on an unauthorized website.
2. **Suspension UX**: When a brand is suspended, should the widget disappear from their website entirely, or should it remain visible but reply with a polite "Service is temporarily unavailable" message? (Disappearing is often better for their end-users, but a visible error creates urgency for the brand owner to pay you).
3. **Grace Period**: If a payment fails, do they suspend immediately, or is there a 3-5 day grace period?
4. **Data Retention**: For cancelled/deleted accounts, do we implement a 30-day soft delete before permanently purging their vector DB chunks to save MongoDB costs?
5. **File Storage**: `build_vector_stores.py` currently uses the local filesystem. For a SaaS, we need to move these source files to Cloud Storage (AWS S3) or store the raw markdown directly in MongoDB (e.g. GridFS or just a `documents` collection). Which approach do you prefer?
