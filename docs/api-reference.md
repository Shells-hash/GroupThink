# API Reference

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

All protected routes require: `Authorization: Bearer <token>`

---

## Auth

### `POST /auth/register`
Create a new account.

**Body:** `{ username, email, password }`
**Returns:** `{ access_token, token_type }`
**Errors:** 409 if username already taken

### `POST /auth/login`
**Body:** `{ username, password }`
**Returns:** `{ access_token, token_type }`
**Errors:** 401 if credentials invalid

### `GET /auth/me` 🔒
**Returns:** `{ id, username, email, created_at }`

---

## Groups

### `GET /groups` 🔒
List all groups the current user belongs to.

### `POST /groups` 🔒
Create a group. Creator is auto-added as owner.
**Body:** `{ name, description? }`

### `GET /groups/{group_id}` 🔒
Group detail including member list.
**Returns:** `{ id, name, description, owner_id, created_at, members: [{ user, role, joined_at }] }`

### `POST /groups/{group_id}/invite` 🔒
Invite a user by username.
**Body:** `{ username }`
**Errors:** 404 if user not found, 409 if already a member

### `DELETE /groups/{group_id}/members/{user_id}` 🔒
Remove a member. Members can remove themselves; owners can remove anyone.

### `DELETE /groups/{group_id}` 🔒
Delete group (owner only). Cascades to threads, messages, plans.

---

## Threads

### `GET /groups/{group_id}/threads` 🔒
List threads in a group.

### `POST /groups/{group_id}/threads` 🔒
Create a thread.
**Body:** `{ title }`

### `DELETE /groups/{group_id}/threads/{thread_id}` 🔒
Delete a thread (creator or group owner only).

---

## Messages

### `GET /threads/{thread_id}/messages` 🔒
Paginated message history.
**Query params:** `limit` (default 50, max 100), `before_id` (for pagination)
**Returns:** Array of `{ id, thread_id, user_id, username, content, is_ai, created_at }`

---

## Plans

### `GET /plans/{thread_id}` 🔒
Get the current plan for a thread.
**Errors:** 404 if not yet generated

### `POST /plans/{thread_id}/generate` 🔒
Trigger AI plan generation from full thread history. Creates or updates the plan.
**Returns:** `{ id, thread_id, goals, action_items, decisions, summary, generated_at }`

---

## WebSocket

### `WS /ws/{thread_id}?token={jwt}`

Connect to a thread's real-time chat room. JWT is passed as query param (browser WebSocket limitation).

**Send:**
```json
{ "type": "message", "content": "Hello @ai what should we do first?" }
```

**Receive (human message):**
```json
{
  "type": "message",
  "message_id": 42,
  "thread_id": 7,
  "user_id": 3,
  "username": "alice",
  "content": "Hello @ai what should we do first?",
  "is_ai": false,
  "created_at": "2026-03-20T14:00:00"
}
```

**Receive (AI thinking indicator):**
```json
{ "type": "ai_thinking", "thread_id": 7 }
```

**Receive (AI message):**
```json
{
  "type": "message",
  "message_id": 43,
  "thread_id": 7,
  "user_id": null,
  "username": "GroupThink AI",
  "content": "Great question! Here are some suggestions...",
  "is_ai": true,
  "created_at": "2026-03-20T14:00:02"
}
```

**Close codes:**
- `4001` — Invalid or missing JWT
- `4003` — Not a member of this group
- `4004` — Thread not found
