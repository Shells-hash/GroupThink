# AI Integration

GroupThink uses the Anthropic Python SDK to power two distinct AI capabilities.

## 1. Inline @ai Reply

**Trigger:** Any message containing `@ai` (case-insensitive)
**File:** `backend/services/ai_service.py` → `get_ai_reply()`

### How it works

1. Fetches the last `AI_CONTEXT_WINDOW` messages from the thread (default: 20)
2. Converts them to Anthropic message format (`user`/`assistant` roles)
3. Consecutive same-role messages are merged (Anthropic requires alternating roles)
4. Sends to `claude-sonnet-4-6` with a facilitator system prompt
5. Returns the text response

### System prompt (facilitator)

The AI is instructed to act as a planning facilitator:
- Concise, structured responses
- Use bullet points for lists
- Ask a clarifying question if the group seems stuck
- Nudge toward actionable outcomes
- Keep responses under 300 words

## 2. Plan Generation

**Trigger:** `POST /plans/{thread_id}/generate`
**File:** `backend/services/ai_service.py` → `generate_plan()`

### How it works

1. Fetches ALL messages in the thread
2. Builds a labeled transcript (`[username]: message content`)
3. Sends to `claude-sonnet-4-6` with a structured extraction prompt
4. The prompt asks Claude to return ONLY valid JSON with this schema:
   ```json
   {
     "goals": ["string"],
     "action_items": [{"task": "string", "assignee": "string|null", "due_date": "string|null"}],
     "decisions": ["string"],
     "summary": "string"
   }
   ```
5. JSON is parsed and saved to the `plans` table by `plan_service.py`
6. If Claude wraps output in markdown code fences, they are stripped

## Model Choice

Both features use `claude-sonnet-4-6` — fast, cost-efficient, and highly capable at structured extraction and facilitation tasks.

## Prompt Design Notes

- The plan extraction prompt explicitly says "return ONLY valid JSON — no other text" to prevent prose wrapping
- The facilitator prompt caps responses at 300 words to keep the chat focused
- Thread context is limited to the last N messages for `@ai` replies to keep latency low and costs manageable
