"""
Tool definitions in Anthropic API format.

Each tool has a name, description, and input_schema (JSON Schema).
Descriptions are written to guide the model on WHEN and HOW to use each tool.
"""

TOOL_DEFINITIONS: list[dict] = [
    # ── KB (Knowledge Base) ──────────────────────────────────────────────
    {
        "name": "kb_search",
        "description": (
            "Search the personal knowledge base (Notion pages, session summaries, "
            "project docs, health/medical records, finance data, personal facts — 500+ chunks). "
            "Use FIRST for ANY question about: projects, architecture, past conversations, "
            "technical plans, tools, workflows, health/medical info (diagnoses, test results, "
            "appointments), finances/investments, personal context about the user or his family. "
            "IMPORTANT: if the first results are about a family member (e.g. father) — "
            "call kb_search again with the user's own name (Давлат / Давлатбек) to find his personal data. "
            "Returns relevant text chunks ranked by relevance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — describe what you're looking for. Works in Russian and English.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (1-10).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "kb_get_facts",
        "description": (
            "Get stored personal facts (name, preferences, projects, tech stack, etc). "
            "Use when you need personal context about the user. "
            "Returns up to 25 key-value facts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "kb_add_document",
        "description": (
            "Save text into the personal knowledge base (KB) — the PRIMARY way to "
            "remember anything long-term. Use this WHENEVER the user shares something "
            "worth keeping: facts, events, plans, people, health info, relationship "
            "notes, decisions, conversation summaries — or explicitly says "
            "'запомни' / 'запиши' / 'сохрани' / 'remember this'. "
            "This is the DEFAULT store (not Notion, not short-term memory). "
            "Write a clear, self-contained title and well-structured text "
            "(Markdown ok) so it's findable later via kb_search. "
            "Always confirm to the user what you saved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short, specific, self-contained title (the user will search by it later).",
                },
                "text": {
                    "type": "string",
                    "description": "The full content to remember. Structure it clearly; Markdown is fine.",
                },
                "doc_date": {
                    "type": "string",
                    "description": "Date of the fact/event in YYYY-MM-DD (optional, defaults to today).",
                },
            },
            "required": ["title", "text"],
        },
    },
    {
        "name": "kb_add_file",
        "description": (
            "Index a file that the user sent (PDF, .txt, .md) into the knowledge base. "
            "The file has already been downloaded to the server — pass its absolute "
            "'path' (you are given it in the message). Use when the user sends a "
            "document and wants it remembered/analyzed, or asks to save a file to KB. "
            "Always confirm what was indexed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the downloaded file on the server.",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the document (optional, defaults to filename).",
                },
                "doc_date": {
                    "type": "string",
                    "description": "Document date YYYY-MM-DD (optional, defaults to today).",
                },
            },
            "required": ["path"],
        },
    },
    # ── Notion ────────────────────────────────────────────────────────────
    {
        "name": "notion_search",
        "description": (
            "Search Notion workspace for pages by title or content. "
            "Use for finding specific pages, tasks, or notes. "
            "Returns page titles, URLs, and snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search text — page title or content keywords.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "notion_create_task",
        "description": (
            "Create a new task/page in the Notion tasks database. "
            "Use ONLY when the user EXPLICITLY mentions Notion or asks to create a task/todo there. "
            "Do NOT use this for general 'remember this' or 'save this' requests — "
            "those go to KB (kb_add_document) by default."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title.",
                },
                "description": {
                    "type": "string",
                    "description": "Task description or details (optional).",
                    "default": "",
                },
            },
            "required": ["title"],
        },
    },
    # ── Web Search ────────────────────────────────────────────────────────
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo. Use for current events, "
            "facts not in the knowledge base, documentation lookups, "
            "or any information that requires up-to-date web data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in any language.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (1-10).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    # ── Memory ────────────────────────────────────────────────────────────
    {
        "name": "memory_store",
        "description": (
            "DEPRECATED for general use — prefer kb_add_document for almost everything. "
            "This is a tiny local key-value store, separate from the searchable KB. "
            "Only use it for very short bot-operational settings (e.g. 'preferred reply "
            "language: Russian'). Any real content — facts, events, people, notes — "
            "must go to kb_add_document instead so it lands in the searchable KB."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short key/category (e.g., 'tech_stack', 'sister_name', 'preference').",
                },
                "value": {
                    "type": "string",
                    "description": "The fact or information to remember.",
                },
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "memory_recall",
        "description": (
            "Search long-term memory for stored facts. "
            "Use when you need to recall something the user told you previously."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — keyword or topic to look for in memory.",
                },
            },
            "required": ["query"],
        },
    },
]
