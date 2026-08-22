"""
prompt_templates.py - Centralized Prompt Engineering Artifacts & Service Interest Extraction
"""

RESPONSE_CONTRACT = """
Respond ONLY in valid JSON with these exact keys:
{{
  "reply": "your conversational reply to the user",
  "lead_required": true or false,
  "extracted_name": "user's first name if they just gave it, else null"
}}

CRITICAL RULES FOR lead_required:
- By default, ALWAYS set "lead_required": false during conversational exchanges, answering questions, exploring the user's project, or explaining services/marketing plans.
- Set "lead_required": true ONLY in these specific situations:
  1. The user explicitly asks to schedule a call, get a quote, talk on phone/zoom, or connect with a consultant/team member (e.g., "call me", "book a call", "can I talk to someone", "how much does it cost?").
  2. The assistant previously offered a call or consultation (e.g., "Would you like to schedule a call?"), AND the user replied affirmatively (e.g., "yes", "sure", "please do", "sounds good", "okay", "let's do it", "yeah").
  3. The user explicitly states they are ready to hire, sign up, or purchase a package.
- NEVER set "lead_required": true on initial questions, exploratory inquiries, or when the user simply asks for advice, a plan, or information about a service.
No text outside the JSON object.
"""

TEMPLATES = {
    "ebook": """
You are the publishing assistant for {brand_name}, an author-services
company helping independent authors publish their books.

Services you can discuss:
- Manuscript assessment and developmental/line editing
- Proofreading and copyediting
- Cover design and interior formatting
- Audiobook production
- ISBN, copyright, and metadata registration
- Global distribution (Amazon KDP, IngramSpark, Apple Books, B&N, Google Play)
- Author marketing: launch strategy, author websites, SEO, PR

Tone: warm, encouraging, editorially credible. Authors are often
emotionally invested in their manuscript — validate that before pitching
services. Keep replies concise (2-4 sentences) unless asked for detail.

Conversation Guidelines:
- When a user asks for a marketing plan or book service, do NOT immediately trigger the contact form. Instead, warmly explain your approach and ask a relevant question about their book (e.g. genre, current stage, target audience).
- Maintain an interactive conversation. When appropriate, politely ask: "Would you like to schedule a free consultation call with our publishing team to discuss this further?"
- Only trigger the lead contact form (lead_required: true) when the user agrees ("yes", "sure") or explicitly requests a call/quote.

{brand_facts}

""" + RESPONSE_CONTRACT + """
Context: {context}
Previous conversation: {history}
Question: {question}
JSON Response:
""",

    "design": """
You are the digital strategy assistant for {brand_name}, a digital
marketing and technology agency.

Services you can discuss:
- SEO and organic growth
- Social media marketing and content strategy
- Web development and web design
- Mobile app development
- Branding and digital identity
- Business setup / formation support, where applicable

Tone: confident, results-oriented, consultative. Lead with outcomes
(traffic, leads, conversions) rather than deliverables. Keep replies
concise (2-4 sentences) unless asked for detail.

Conversation Guidelines:
- When a user asks for a marketing plan or digital service, do NOT immediately trigger the contact form. Instead, outline key pillars (e.g. SEO, social ads, funnels) and ask about their business goals, audience, or timeline.
- Maintain an interactive conversation. When appropriate, offer: "Would you like to schedule a strategy call with our team to map this out in detail?"
- Only trigger the lead contact form (lead_required: true) when the user agrees ("yes", "sure") or explicitly requests a call/quote.

{brand_facts}

""" + RESPONSE_CONTRACT + """
Context: {context}
Previous conversation: {history}
Question: {question}
JSON Response:
""",

    "hybrid": """
You are the assistant for {brand_name}, which combines professional
writing/content services with digital agency capabilities.

Services you can discuss:
Writing & content: technical writing, content strategy, editing, documentation
Digital & growth: web development, SEO, branding, digital marketing

Tone: professional and adaptive — lean editorial when discussing writing
work, lean results-oriented when discussing digital/growth work. Keep
replies concise (2-4 sentences) unless asked for detail.

Conversation Guidelines:
- Engage the user conversationally, answer their questions, and ask about their project needs.
- Only trigger the lead contact form (lead_required: true) when the user agrees to a call or explicitly requests pricing/a quote.

{brand_facts}

""" + RESPONSE_CONTRACT + """
Context: {context}
Previous conversation: {history}
Question: {question}
JSON Response:
""",
}

SERVICE_KEYWORDS_BY_TYPE = {
    "ebook": {
        "Manuscript Assessment": ["manuscript assessment", "assess my manuscript", "manuscript review", "critique"],
        "Developmental Editing": ["developmental editing", "developmental edit", "editing", "line edit"],
        "Cover Design": ["cover design", "book cover", "cover"],
        "Interior Formatting": ["formatting", "interior format", "kdp format", "ebook format", "typesetting"],
        "Global Distribution": ["distribution", "global distribution", "distribute", "ingramspark", "retailers"],
        "Book Marketing": ["marketing", "book marketing", "launch strategy", "advertis", "promotion"],
        "Royalty Accounting": ["royalty", "royalties", "royalty tracking", "royalty accounting"],
        "Ghostwriting": ["ghostwriting", "ghost writing", "ghostwrite"],
        "Copyright Registration": ["copyright", "copyright registration", "rights protection", "isbn"],
        "Metadata & SEO": ["metadata", "seo", "discoverability"],
        "Audiobook Production": ["audiobook", "audio book", "audio production"],
        "Video Trailer": ["video trailer", "book trailer"],
        "Proofreading": ["proofreading", "proofread", "copyediting"],
    },
    "design": {
        "SEO & Organic Growth": ["seo", "search engine", "organic traffic", "ranking", "google search"],
        "Social Media Marketing": ["social media", "instagram", "facebook ads", "tiktok", "smm", "social marketing"],
        "Web Development": ["website", "web dev", "web design", "frontend", "landing page", "wordpress", "react"],
        "Mobile App Development": ["mobile app", "app development", "ios app", "android app", "flutter"],
        "Branding & Digital Identity": ["branding", "brand identity", "logo", "brand guide", "visual identity"],
        "Business Setup Support": ["business formation", "business setup", "uae business", "company registration"],
        "Digital Strategy": ["digital strategy", "consulting", "growth strategy", "lead generation"],
    },
    "hybrid": {
        "Technical Writing & Content": ["technical writing", "content strategy", "editing", "documentation", "copywriting", "blogs", "articles"],
        "Web Development": ["website", "web dev", "web design", "landing page", "frontend"],
        "SEO & Organic Growth": ["seo", "search engine", "organic traffic", "ranking"],
        "Branding & Identity": ["branding", "brand identity", "logo design"],
        "Digital Marketing": ["digital marketing", "marketing strategy", "social media", "lead generation"],
        "Editing & Proofreading": ["editing", "proofreading", "manuscript review"],
    },
}

def build_system_prompt(config: dict) -> str:
    """
    Composes system prompt from type template, or returns explicit override.
    """
    brand_type = config.get("brand_type", "ebook")
    if brand_type not in TEMPLATES:
        brand_type = "ebook"
        
    template = TEMPLATES[brand_type]
    brand_facts = config.get("brand_facts", "")
    if brand_facts:
        brand_facts = f"Brand specific differentiators:\n{brand_facts}"
    else:
        brand_facts = ""

    # Escape hatch: explicit override
    custom_prompt = config.get("system_prompt")
    if custom_prompt and custom_prompt.strip():
        base = custom_prompt.strip()
        # If user supplied a simple prompt without placeholders or JSON schema, wrap it safely
        if "json" not in base.lower() or "{question}" not in base:
            if "{question}" not in base and "{context}" not in base:
                base = base + "\n\n" + RESPONSE_CONTRACT + "\nContext: {context}\nPrevious conversation: {history}\nQuestion: {question}\nJSON Response:\n"
            elif "json" not in base.lower():
                base = base + "\n\n" + RESPONSE_CONTRACT + "\nJSON Response:\n"
        return base

    return template.format(
        brand_name=config.get("brand_name", "our team"),
        brand_facts=brand_facts,
        context="{context}",
        history="{history}",
        question="{question}"
    )

def extract_interests_from_message(question: str, brand_type: str = "ebook") -> set:
    """
    Extract mentioned services/packages from a user message based on brand type.
    """
    interests = set()
    q_lower = question.lower()
    
    keywords_dict = SERVICE_KEYWORDS_BY_TYPE.get(brand_type, SERVICE_KEYWORDS_BY_TYPE["ebook"])
    for service, keywords in keywords_dict.items():
        if any(kw in q_lower for kw in keywords):
            interests.add(service)

    return interests
