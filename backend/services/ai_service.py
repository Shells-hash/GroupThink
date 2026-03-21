import json
import anthropic
from sqlalchemy.orm import Session
from backend.config import get_settings
from backend.models.message import Message
from backend.models.plan_message import PlanMessage
from backend.services.message_service import get_recent_messages_for_context, get_all_messages_for_thread

settings = get_settings()

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


def _build_context_messages(messages: list[Message]) -> list[dict]:
    result = []
    for msg in messages:
        role = "assistant" if msg.is_ai else "user"
        name = "GroupThink AI" if msg.is_ai else (msg.user.username if msg.user else "unknown")
        result.append({"role": role, "content": f"[{name}]: {msg.content}"})
    return result


def get_ai_reply(db: Session, thread_id: int, triggering_message: str, username: str) -> str:
    """Generate an @ai inline reply with recent thread context."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    recent = get_recent_messages_for_context(db, thread_id, settings.ai_context_window)
    context = _build_context_messages(recent)

    # Append the triggering message if not already in context
    if not context or context[-1]["content"] != f"[{username}]: {triggering_message}":
        context.append({"role": "user", "content": f"[{username}]: {triggering_message}"})

    # Anthropic requires alternating roles — merge consecutive same-role messages
    merged: list[dict] = []
    for msg in context:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(dict(msg))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=FACILITATOR_SYSTEM_PROMPT,
        messages=merged,
    )
    return response.content[0].text


def generate_plan(db: Session, thread_id: int) -> dict:
    """Read full thread history and return structured plan as a dict."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    all_messages = get_all_messages_for_thread(db, thread_id)

    if not all_messages:
        return {"goals": [], "action_items": [], "decisions": [], "summary": "No messages yet."}

    transcript_lines = []
    for msg in all_messages:
        speaker = "AI" if msg.is_ai else (msg.user.username if msg.user else "unknown")
        transcript_lines.append(f"[{speaker}]: {msg.content}")
    transcript = "\n".join(transcript_lines)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=PLAN_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


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


def plan_chat_reply(db: Session, thread_id: int, user_message: str, username: str, current_plan: dict | None) -> dict:
    """Send a message in the plan design chat. Returns {reply, plan}."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Load plan conversation history
    history = (
        db.query(PlanMessage)
        .filter(PlanMessage.thread_id == thread_id)
        .order_by(PlanMessage.created_at.asc())
        .all()
    )

    # Build message list from history
    messages: list[dict] = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Add context about the current plan state if it exists
    context_prefix = ""
    if current_plan:
        context_prefix = f"[Current plan state: {json.dumps(current_plan)}]\n\n"

    messages.append({"role": "user", "content": context_prefix + f"[{username}]: {user_message}"})

    # Merge consecutive same-role messages
    merged: list[dict] = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(dict(msg))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=PLAN_CHAT_SYSTEM_PROMPT,
        messages=merged,
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)


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


def draft_document(db: Session, thread_id: int, title: str, existing_content: str, instructions: str = "") -> str:
    """Generate or improve a planning document based on thread context."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    all_messages = get_all_messages_for_thread(db, thread_id)

    transcript = ""
    if all_messages:
        lines = []
        for msg in all_messages[-40:]:
            speaker = "AI" if msg.is_ai else (msg.user.username if msg.user else "unknown")
            lines.append(f"[{speaker}]: {msg.content}")
        transcript = "\n".join(lines)

    user_content = f"Document title: {title}\n"
    if transcript:
        user_content += f"\nGroup discussion context:\n{transcript}\n"
    if existing_content:
        user_content += f"\nExisting content to improve:\n{existing_content}\n"
    if instructions:
        user_content += f"\nSpecific instructions: {instructions}\n"
    user_content += "\nWrite the complete Markdown document."

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=DOC_DRAFT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text


def get_plan_chat_stream(messages_for_ai: list[dict], current_plan: dict | None):
    """Returns a streaming Anthropic context manager for plan chat.
    messages_for_ai: list of {role, content} dicts already prepared for the API.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context_prefix = ""
    if current_plan:
        context_prefix = f"[Current plan: {json.dumps(current_plan)}]\n\n"

    # Inject plan context into last user message
    augmented = list(messages_for_ai)
    if augmented and augmented[-1]["role"] == "user":
        augmented[-1] = {"role": "user", "content": context_prefix + augmented[-1]["content"]}

    return client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1536,
        system=PLAN_CHAT_CONVERSATIONAL_PROMPT,
        messages=augmented,
    )


def extract_plan_update(conversation_messages: list[dict], current_plan: dict | None) -> dict:
    """Fast plan extraction using Haiku after a streaming reply."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    current = json.dumps(current_plan) if current_plan else "{}"
    transcript = "\n".join(
        f"[{m['role']}]: {m['content']}" for m in conversation_messages[-12:]
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=PLAN_UPDATE_PROMPT,
        messages=[{"role": "user", "content": f"Current plan:\n{current}\n\nConversation:\n{transcript}"}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except Exception:
        return current_plan or {"goals": [], "action_items": [], "decisions": [], "summary": ""}


async def get_ai_reply_stream(db: Session, thread_id: int, triggering_message: str, username: str):
    """Async generator that yields tokens for streaming @ai replies."""
    import anthropic as _anthropic
    async_client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    recent = get_recent_messages_for_context(db, thread_id, settings.ai_context_window)
    context = _build_context_messages(recent)

    if not context or context[-1]["content"] != f"[{username}]: {triggering_message}":
        context.append({"role": "user", "content": f"[{username}]: {triggering_message}"})

    merged: list[dict] = []
    for msg in context:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(dict(msg))

    full_text = ""
    async with async_client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=768,
        system=FACILITATOR_SYSTEM_PROMPT,
        messages=merged,
    ) as stream:
        async for token in stream.text_stream:
            full_text += token
            yield token
    return  # full_text is accumulated by the caller
