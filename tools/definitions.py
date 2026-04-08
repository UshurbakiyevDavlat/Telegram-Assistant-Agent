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
            "project docs — 500+ chunks). Use FIRST for any question about: "
            "projects, architecture decisions, past conversations, technical plans, "
            "tools, workflows. Returns relevant text chunks ranked by relevance."
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
            "Use when the user asks to create a task, reminder, or todo."
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
            "Store a fact or preference for long-term memory. "
            "Use when the user shares personal info, preferences, or asks to remember something. "
            "Examples: 'my stack is Python + Go', 'preferred language: Russian', "
            "'sister's name is Aisha'. Persists across bot restarts."
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
