import json
from sqlalchemy.orm import Session
from backend.config import get_settings
from backend.models.message import Message
from backend.models.plan_message import PlanMessage
from backend.services.message_service import get_recent_messages_for_context, get_all_messages_for_thread

settings = get_settings()

# ── Prompts ──────────────────────────────────────────────────────────────────

FACILITATOR_SYSTEM_PROMPT = """You are GroupThink AI, a collaborative planning assistant embedded in a group chat.
Your role is to help groups clarify ideas, identify goals, assign action items, and reach concrete decisions.

Guidelines:
- Use **Markdown formatting** in all responses: bold for key points, bullet lists for items, headers for structure.
- When illustrating flows, processes, or timelines, use **Mermaid diagrams** in fenced code blocks (```mermaid).
  Supported types: flowchart TD, sequenceDiagram, gantt, mindmap, erDiagram.
- Be concise and structured. If the group is stuck or vague, ask one clarifying question.
- Acknowledge the specific question or message that triggered you.
- Nudge the group toward actionable outcomes."""

PLAN_EXTRACTION_PROMPT = """Read the following group planning discussion carefully.
Extract and return ONLY valid JSON with this exact schema — no other text:

{
  "goals": ["string", ...],
  "action_items": [{"task": "string", "assignee": "string or null", "due_date": "string or null"}, ...],
  "decisions": ["string", ...],
  "summary": "string"
}

Rules:
- goals: High-level objectives the group wants to achieve
- action_items: Concrete tasks, with assignee if mentioned, due_date if mentioned
- decisions: Things the group has agreed on or decided
- summary: 2-4 sentence narrative of what the discussion is about and where it stands"""

PLAN_CHAT_CONVERSATIONAL_PROMPT = """You are a plan design assistant for GroupThink. You help teams design, refine, and structure plans through natural conversation.

Be conversational, thoughtful, and helpful. Use **markdown formatting** — headers, bullet lists, bold text. Include **Mermaid diagrams** when they help illustrate flows, timelines, or structures (use ```mermaid code blocks with flowchart TD, gantt, sequenceDiagram, or mindmap).

Ask clarifying questions when needed. Reference the current plan state and suggest concrete improvements. Help the group think through implications and next steps."""

PLAN_UPDATE_PROMPT = """Read this planning conversation and return an updated plan as ONLY valid JSON — no other text:

{
  "goals": ["goal 1", ...],
  "action_items": [{"task": "...", "assignee": "name or null", "due_date": "date or null"}, ...],
  "decisions": ["decision 1", ...],
  "summary": "2-4 sentence summary"
}

Rules:
- Keep all previously established items unless explicitly changed
- Add new goals, action items, or decisions mentioned in the latest exchange
- Update summary to reflect the current state of the plan"""

PLAN_CHAT_SYSTEM_PROMPT = """You are a plan design assistant for GroupThink. You help teams design, refine, and structure plans through conversation — like working with a smart collaborator.

After EVERY response you MUST return ONLY valid JSON in this exact format (no other text, no markdown fences):
{
  "reply": "your conversational response here — use markdown formatting, bold for emphasis, bullet lists for structure. Use mermaid code blocks for diagrams when helpful.",
  "plan": {
    "goals": ["goal 1", "goal 2"],
    "action_items": [{"task": "task description", "assignee": "name or null", "due_date": "date string or null"}],
    "decisions": ["decision 1"],
    "summary": "2-4 sentence summary of the plan"
  }
}

Guidelines:
- reply: Be conversational and helpful. Use markdown. Include mermaid diagrams (flowchart, gantt, etc.) when they add value.
- plan: Always reflect the FULL plan state. Update it with each exchange.
- If nothing concrete has been decided yet, keep arrays empty but still include the plan object."""

DOC_DRAFT_SYSTEM_PROMPT = """You are a document writing assistant for GroupThink. You help teams create clear, well-structured planning documents.

Write in Markdown format. Use:
- # and ## headers for document structure
- **Bold** for important points
- Bullet lists and numbered lists
- Tables for comparisons or structured data
- Mermaid diagrams for flows, timelines, processes, or relationships:
  - flowchart TD — for process flows and decision trees
  - gantt — for project timelines and schedules
  - sequenceDiagram — for interaction flows
  - mindmap — for brainstorming and idea organization

Write a complete, professional document. Be thorough but focused."""


# ── Provider abstraction ──────────────────────────────────────────────────────

def _main_model() -> str:
    p = settings.model_provider
    if p == "groq":       return settings.groq_model
    if p == "together":   return settings.together_model
    if p == "ollama":     return settings.ollama_model
    return "claude-sonnet-4-6"


def _fast_model() -> str:
    """Cheaper/faster model for quick extractions."""
    p = settings.model_provider
    if p == "groq":       return settings.groq_fast_model
    if p == "together":   return settings.together_fast_model
    if p == "ollama":     return settings.ollama_model
    return "claude-haiku-4-5-20251001"


def _openai_client(fast: bool = False):
    """Return an openai.OpenAI client pointed at the configured provider."""
    from openai import OpenAI
    p = settings.model_provider
    if p == "groq":
        return OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
    if p == "together":
        return OpenAI(api_key=settings.together_api_key, base_url="https://api.together.xyz/v1")
    if p == "ollama":
        return OpenAI(api_key="ollama", base_url=settings.ollama_base_url)
    raise ValueError(f"Unknown provider for openai client: {p}")


def _complete(messages: list[dict], system: str, max_tokens: int, fast: bool = False) -> str:
    """Non-streaming completion — works with any configured provider."""
    p = settings.model_provider
    model = _fast_model() if fast else _main_model()

    if p == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages
        )
        return response.content[0].text
    else:
        client = _openai_client(fast)
        oai_messages = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=oai_messages
        )
        return response.choices[0].message.content


def _stream_tokens(messages: list[dict], system: str, max_tokens: int):
    """Sync generator that yields text tokens — works with any provider."""
    p = settings.model_provider
    model = _main_model()

    if p == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        with client.messages.stream(
            model=model, max_tokens=max_tokens, system=system, messages=messages
        ) as stream:
            for token in stream.text_stream:
                yield token
    else:
        client = _openai_client()
        oai_messages = [{"role": "system", "content": system}] + messages
        stream = client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=oai_messages, stream=True
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


async def _async_stream_tokens(messages: list[dict], system: str, max_tokens: int):
    """Async generator that yields text tokens — works with any provider."""
    p = settings.model_provider
    model = _main_model()

    if p == "anthropic":
        import anthropic as _anthropic
        async_client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        async with async_client.messages.stream(
            model=model, max_tokens=max_tokens, system=system, messages=messages
        ) as stream:
            async for token in stream.text_stream:
                yield token
    else:
        from openai import AsyncOpenAI
        p2 = settings.model_provider
        if p2 == "groq":
            async_client = AsyncOpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
        elif p2 == "together":
            async_client = AsyncOpenAI(api_key=settings.together_api_key, base_url="https://api.together.xyz/v1")
        else:  # ollama
            async_client = AsyncOpenAI(api_key="ollama", base_url=settings.ollama_base_url)

        oai_messages = [{"role": "system", "content": system}] + messages
        stream = await async_client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=oai_messages, stream=True
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


def _merge_roles(messages: list[dict]) -> list[dict]:
    """Merge consecutive same-role messages (required by Anthropic API)."""
    merged: list[dict] = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(dict(msg))
    return merged


def _strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


# ── Public AI functions ───────────────────────────────────────────────────────

def _build_context_messages(messages: list[Message]) -> list[dict]:
    result = []
    for msg in messages:
        role = "assistant" if msg.is_ai else "user"
        name = "GroupThink AI" if msg.is_ai else (msg.user.username if msg.user else "unknown")
        result.append({"role": role, "content": f"[{name}]: {msg.content}"})
    return result


def get_ai_reply(db: Session, thread_id: int, triggering_message: str, username: str) -> str:
    """Generate an @ai inline reply with recent thread context."""
    recent = get_recent_messages_for_context(db, thread_id, settings.ai_context_window)
    context = _build_context_messages(recent)
    if not context or context[-1]["content"] != f"[{username}]: {triggering_message}":
        context.append({"role": "user", "content": f"[{username}]: {triggering_message}"})
    return _complete(_merge_roles(context), FACILITATOR_SYSTEM_PROMPT, 512)


async def get_ai_reply_stream(db: Session, thread_id: int, triggering_message: str, username: str):
    """Async generator that yields tokens for streaming @ai replies."""
    recent = get_recent_messages_for_context(db, thread_id, settings.ai_context_window)
    context = _build_context_messages(recent)
    if not context or context[-1]["content"] != f"[{username}]: {triggering_message}":
        context.append({"role": "user", "content": f"[{username}]: {triggering_message}"})
    async for token in _async_stream_tokens(_merge_roles(context), FACILITATOR_SYSTEM_PROMPT, 768):
        yield token


def generate_plan(db: Session, thread_id: int) -> dict:
    """Read full thread history and return structured plan as a dict."""
    all_messages = get_all_messages_for_thread(db, thread_id)
    if not all_messages:
        return {"goals": [], "action_items": [], "decisions": [], "summary": "No messages yet."}

    transcript_lines = []
    for msg in all_messages:
        speaker = "AI" if msg.is_ai else (msg.user.username if msg.user else "unknown")
        transcript_lines.append(f"[{speaker}]: {msg.content}")

    raw = _complete(
        [{"role": "user", "content": "\n".join(transcript_lines)}],
        PLAN_EXTRACTION_PROMPT,
        1024,
    )
    return json.loads(_strip_json_fences(raw))


def plan_chat_reply(db: Session, thread_id: int, user_message: str, username: str, current_plan: dict | None) -> dict:
    """Non-streaming plan chat reply (fallback). Returns {reply, plan}."""
    history = (
        db.query(PlanMessage)
        .filter(PlanMessage.thread_id == thread_id)
        .order_by(PlanMessage.created_at.asc())
        .all()
    )
    messages: list[dict] = [{"role": m.role, "content": m.content} for m in history]
    context_prefix = f"[Current plan state: {json.dumps(current_plan)}]\n\n" if current_plan else ""
    messages.append({"role": "user", "content": context_prefix + f"[{username}]: {user_message}"})
    raw = _complete(_merge_roles(messages), PLAN_CHAT_SYSTEM_PROMPT, 1024)
    return json.loads(_strip_json_fences(raw))


def get_plan_chat_stream(messages_for_ai: list[dict], current_plan: dict | None):
    """Returns a sync token generator for streaming plan chat replies."""
    augmented = list(messages_for_ai)
    if current_plan and augmented and augmented[-1]["role"] == "user":
        augmented[-1] = {
            "role": "user",
            "content": f"[Current plan: {json.dumps(current_plan)}]\n\n" + augmented[-1]["content"],
        }
    return _stream_tokens(augmented, PLAN_CHAT_CONVERSATIONAL_PROMPT, 1536)


def extract_plan_update(conversation_messages: list[dict], current_plan: dict | None) -> dict:
    """Fast plan extraction after a streaming reply."""
    current = json.dumps(current_plan) if current_plan else "{}"
    transcript = "\n".join(f"[{m['role']}]: {m['content']}" for m in conversation_messages[-12:])
    raw = _complete(
        [{"role": "user", "content": f"Current plan:\n{current}\n\nConversation:\n{transcript}"}],
        PLAN_UPDATE_PROMPT,
        512,
        fast=True,
    )
    try:
        return json.loads(_strip_json_fences(raw))
    except Exception:
        return current_plan or {"goals": [], "action_items": [], "decisions": [], "summary": ""}


def draft_document(db: Session, thread_id: int, title: str, existing_content: str, instructions: str = "") -> str:
    """Generate or improve a planning document based on thread context."""
    all_messages = get_all_messages_for_thread(db, thread_id)
    transcript = ""
    if all_messages:
        lines = [
            f"[{'AI' if m.is_ai else (m.user.username if m.user else 'unknown')}]: {m.content}"
            for m in all_messages[-40:]
        ]
        transcript = "\n".join(lines)

    user_content = f"Document title: {title}\n"
    if transcript:
        user_content += f"\nGroup discussion context:\n{transcript}\n"
    if existing_content:
        user_content += f"\nExisting content to improve:\n{existing_content}\n"
    if instructions:
        user_content += f"\nSpecific instructions: {instructions}\n"
    user_content += "\nWrite the complete Markdown document."

    return _complete([{"role": "user", "content": user_content}], DOC_DRAFT_SYSTEM_PROMPT, 2048)
