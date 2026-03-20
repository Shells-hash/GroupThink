# Architecture

## Overview

GroupThink is a standard client-server web app with a real-time layer added via WebSockets.

```
Browser (Vanilla JS SPA)
        │
        ├── REST (fetch)        → FastAPI HTTP routes
        └── WebSocket           → FastAPI WebSocket route
                                        │
                                  SQLAlchemy ORM
                                        │
                                   SQLite (dev)
                                   PostgreSQL (prod)
                                        │
                                  Anthropic SDK
                                        │
                               Claude Sonnet (claude-sonnet-4-6)
```

## Request Flow: Normal Message

1. User types a message and hits Send
2. Browser sends `{"type":"message","content":"..."}` over WebSocket
3. `routers/websocket.py` receives it, calls `message_service.save_message()`
4. Message is persisted to `messages` table
5. `ConnectionManager.broadcast()` sends the message to all connected clients in the same thread

## Request Flow: @ai Message

Same as above, plus:

6. Server detects `@ai` in content
7. Broadcasts `{"type":"ai_thinking"}` to show indicator in UI
8. Calls `ai_service.get_ai_reply()` with last 20 messages as context
9. Sends request to Anthropic API (synchronous — the WS loop awaits the response)
10. Saves AI response to `messages` table with `is_ai=True`
11. Broadcasts AI message to all clients

## Request Flow: Generate Plan

1. User clicks "Generate Plan" in Plan view
2. Browser POSTs to `POST /plans/{thread_id}/generate`
3. `plan_service.generate_and_save_plan()` calls `ai_service.generate_plan()`
4. AI service fetches ALL messages in the thread, builds transcript
5. Sends structured extraction prompt to Anthropic API
6. Parses JSON response into `Plan` model
7. Upserts the `plans` table row
8. Returns `PlanOut` schema to browser

## Scaling Path (v2)

Current v1 runs with a single Uvicorn worker and in-process `ConnectionManager`. To scale:

1. Switch `DATABASE_URL` to PostgreSQL
2. Add Redis as a pub/sub broker
3. Replace `ConnectionManager.broadcast()` with Redis pub/sub so multiple workers can share message delivery
4. Run multiple Uvicorn workers behind nginx
5. Use Alembic for migrations (see `backend/database/migrations/README.md`)
