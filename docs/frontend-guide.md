# Frontend Guide

## Overview

The frontend is a single-page app using plain ES modules — no build step, no bundler, no framework. Files are served as static assets by FastAPI.

## Module Layout

```
frontend/js/
├── app.js          # Entry point: registers routes, auth guard, renders shell
├── router.js       # Hash-based client router (#/groups, #/groups/1/threads/2)
├── state.js        # Centralised in-memory state object
├── api.js          # Thin REST client wrapping fetch + JWT injection
├── ws.js           # WebSocket client with reconnect logic
└── views/
    ├── auth.js     # Login and register pages
    ├── groups.js   # Group sidebar + create/invite modals
    ├── thread-list.js  # Thread sidebar + create modal
    ├── chat.js     # Chat view + WebSocket message handling
    └── plan.js     # Plan view with generate button
```

## Routing

Hash-based routing via `router.js`. Routes are registered with `route(pattern, handler)`. Patterns support `:param` segments:

```js
route("/groups/:groupId/threads/:threadId", ({ groupId, threadId }) => { ... });
```

Navigate programmatically: `navigate("/groups/1/threads/3")`

## State

`state.js` exports a single mutable object. Views read from and write to it directly. This is intentionally simple — no reactive system needed at this scale.

Key fields: `user`, `token`, `groups`, `activeGroup`, `threads`, `activeThread`, `messages`

## API Client

`api.js` wraps `fetch` with:
- Automatic `Authorization: Bearer` header injection from `state.token`
- JSON body serialization
- Error extraction from `{ detail: "..." }` responses

## WebSocket Client

`ws.js` manages one WebSocket at a time. When switching threads, the old socket is closed and a new one is opened. Automatic reconnect (3s delay) on unexpected close.

Register a message handler: `onWsMessage((msg) => { ... })`
Send: `sendMessage("Hello @ai")`

The `@ai` thinking animation is triggered by `{ type: "ai_thinking" }` messages from the server.

## CSS Architecture

Five CSS files loaded in order:

1. `reset.css` — browser normalization
2. `variables.css` — CSS custom properties (tokens)
3. `layout.css` — app shell grid, auth page layout
4. `components.css` — reusable UI elements (buttons, inputs, modals, sidebar items)
5. `chat.css` — message bubbles, AI thinking indicator, input area
6. `plan.css` — plan section cards, action items, skeleton loading
