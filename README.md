# GroupThink

An AI-powered collaborative planning app for friend groups. Create group chats around topics, let your friends brainstorm together, and use the built-in AI assistant to structure your discussions into clear goals, action items, and decisions.

## Features

- **Group chats** — Create groups, invite friends, start topic threads
- **Real-time messaging** — WebSocket-powered live chat
- **AI assistant** — Type `@ai` in any message to get planning help from Claude
- **Plan view** — One click to turn any discussion into a structured plan with goals, action items, and decisions
- **Clean structure** — Every plan shows what you're trying to achieve, who does what, and what's been decided

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI (Python) |
| AI | Claude Sonnet via Anthropic SDK |
| Database | SQLite (dev) → PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Real-time | WebSockets |
| Frontend | Vanilla HTML/CSS/JS (no framework, no build step) |

## Project Structure

```
GroupThink/
├── backend/          # FastAPI app
│   ├── models/       # SQLAlchemy ORM models
│   ├── schemas/      # Pydantic request/response schemas
│   ├── routers/      # API route handlers
│   ├── services/     # Business logic
│   ├── utils/        # WebSocket manager, custom exceptions
│   ├── database/     # DB engine, base, migration notes
│   ├── dependencies.py
│   ├── config.py
│   └── main.py
├── frontend/         # Single-page app (no build step)
│   ├── css/
│   └── js/
│       └── views/
├── tests/            # Pytest test suite
├── docs/             # Architecture, API reference, guides
├── scripts/          # seed_db.py, reset_db.py
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `ANTHROPIC_API_KEY` — your Anthropic API key ([get one here](https://console.anthropic.com))
- `SECRET_KEY` — a random 64-char hex string (run `python -c "import secrets; print(secrets.token_hex(32))"`)

### 4. (Optional) Seed development data

```bash
python scripts/seed_db.py
```

This creates users `alice`, `bob`, `carol` (all password: `password123`) with a sample group and thread.

### 5. Run the server

```bash
uvicorn backend.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Running Tests

```bash
pytest
```

## Using the AI

In any group chat thread, type `@ai` anywhere in your message:

```
Hey @ai, we're trying to decide between two venues — can you help us think through the pros and cons?
```

The AI will respond as a planning facilitator, helping your group clarify ideas and move toward decisions.

To generate a structured plan from the full discussion, click **"View Plan"** in any thread, then **"Generate Plan"**.

## Docs

- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Database Schema](docs/database-schema.md)
- [AI Integration](docs/ai-integration.md)
- [Frontend Guide](docs/frontend-guide.md)
- [Deployment](docs/deployment.md)
