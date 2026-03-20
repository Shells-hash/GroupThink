# Deployment

## Local Development

```bash
# Install deps
pip install -r requirements.txt

# Set up .env
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and a random SECRET_KEY

# Run
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

App: http://localhost:8000
API docs: http://localhost:8000/docs

## Generating a SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `SECRET_KEY` | Yes | JWT signing secret (64 hex chars) |
| `DATABASE_URL` | No | Defaults to `sqlite:///./groupthink.db` |
| `JWT_EXPIRE_DAYS` | No | Token expiry, default 7 |
| `AI_CONTEXT_WINDOW` | No | Messages sent to AI for @ai replies, default 20 |

## Production Considerations

1. **Use PostgreSQL** — change `DATABASE_URL` to a PostgreSQL connection string
2. **Single worker limitation** — the in-process WebSocket manager only works with one Uvicorn worker. For multi-worker setups, replace with Redis pub/sub
3. **CORS** — tighten `allow_origins` in `backend/main.py` to your specific frontend domain
4. **HTTPS** — run behind a reverse proxy (nginx) with TLS; the frontend WebSocket client automatically switches to `wss://` when the page is served over HTTPS

## Running with Multiple Workers (after Redis migration)

```bash
uvicorn backend.main:app --workers 4 --host 0.0.0.0 --port 8000
```
