# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

This is **AgentKit COI** — a WhatsApp AI agent for "Centro Oftalmológico Integral" built using AgentKit. The agent (named "Anto") answers patient inquiries about doctors, hours, insurance coverage, and appointments.

**Current configuration:**
- Business: COI (eye care center in Neuquén, Argentina)
- Agent name: Anto
- Tone: Friendly and casual (using Argentine Spanish voseo)
- Provider: Whapi.cloud
- Database: SQLite (local), PostgreSQL (production via Railway)

---

## Architecture

The agent follows a **provider-agnostic architecture** with clear separation of concerns:

```
WhatsApp client → Whapi.cloud webhook → FastAPI (agent/main.py)
                                            ↓
                                      agent/providers/ (normalizes format)
                                            ↓
                                      agent/memory.py (retrieves conversation history)
                                            ↓
                                      agent/brain.py (calls Claude API)
                                            ↓
                                      config/prompts.yaml (system prompt)
                                            ↓
                                      Claude API (generates response)
                                            ↓
                                      Response sent back via Whapi
```

### Key modules:

- **agent/main.py** — FastAPI server with webhook endpoints. Multiple routes handle different Whapi paths (`/webhook/messages`, `/v1/webhook/messages`, `/webhook/statuses`, etc.)
- **agent/brain.py** — Calls Claude API with system prompt + conversation history. Loads config from YAML files.
- **agent/memory.py** — SQLAlchemy + async SQLite. Stores per-phone conversation history.
- **agent/providers/** — Abstraction layer for WhatsApp providers. Currently using Whapi, but can swap to Meta or Twilio by changing `.env`.
- **config/prompts.yaml** — System prompt with agent personality, doctor info, hours, pricing, insurance coverage.
- **config/business.yaml** — Metadata (business name, agent name, use cases).
- **tests/test_local.py** — Interactive CLI to test agent without needing WhatsApp.

---

## Common Commands

### Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Test agent in terminal (no WhatsApp needed)
python tests/test_local.py

# Run server locally
uvicorn agent.main:app --reload --port 8000

# Check Python version
python3 --version
```

### Docker

```bash
# Build Docker image
docker compose build

# Run in Docker
docker compose up

# View logs
docker compose logs -f agent

# Stop
docker compose down
```

### Database

```bash
# The SQLite database (agentkit.db) is auto-created on first run
# To reset conversation history:
rm agentkit.db
python tests/test_local.py  # Creates new DB
```

---

## Configuration

### `.env` (never commit to Git)

Key variables:

```env
ANTHROPIC_API_KEY=sk-ant-...          # Anthropic Claude API key
WHATSAPP_PROVIDER=whapi               # whapi | meta | twilio
WHAPI_TOKEN=...                       # Whapi.cloud token
PORT=8000                             # Server port
ENVIRONMENT=development               # development | production
DATABASE_URL=sqlite+aiosqlite:///./agentkit.db
```

### `config/prompts.yaml`

The system prompt that defines Anto's personality, knowledge, and behavior. Includes:
- Identity and tone
- Doctor information and restrictions
- Hours and pricing
- Insurance coverage
- Instructions on how to book appointments
- Behavioral rules (always use Argentine voseo, moderate emoji use, etc.)

Update this file to:
- Change agent personality/tone
- Add new doctors or update restrictions
- Update hours or pricing
- Add new instructions

No code restart needed — reloading prompts.yaml applies immediately.

### `config/business.yaml`

Metadata about the business. Simple YAML with business name, agent name, and use cases.

---

## Modifying the Agent

### Change the prompt/personality

Edit `config/prompts.yaml` → system_prompt section. Changes apply immediately (no restart needed).

### Add doctor or pricing information

Update `config/prompts.yaml` in the "Médicos del centro" and "Precios y coberturas" sections.

### Change agent name or tone

Edit `config/prompts.yaml` → Tu identidad section.

### Add new capabilities

Edit `agent/tools.py` to add tool functions. Then reference them in the system prompt so Claude knows they exist.

### Switch WhatsApp provider

1. Change `.env`: `WHATSAPP_PROVIDER=meta` (or `twilio`)
2. Set provider-specific variables in `.env`
3. Update webhook URL in your WhatsApp provider's dashboard
4. Restart server

No code changes needed thanks to the provider abstraction layer.

---

## Deployment

### Railway (current production setup)

1. Push code to GitHub
2. Connect repo to Railway
3. Set environment variables in Railway dashboard:
   - `ANTHROPIC_API_KEY`
   - `WHATSAPP_PROVIDER` (usually `whapi`)
   - Provider token (`WHAPI_TOKEN`, etc.)
   - `ENVIRONMENT=production`
   - `DATABASE_URL` (Railway provides PostgreSQL)

4. Railway auto-builds from Dockerfile
5. Set webhook in Whapi dashboard: `https://your-railway-app.up.railway.app/webhook/messages`

### Local testing before deploy

Always run `python tests/test_local.py` to verify agent behavior before deploying.

---

## Important Notes

- **Never hardcode API keys** — use `.env` via python-dotenv
- **Conversation history is per-phone** — each client has their own SQLite record
- **No external integrations yet** — agent only responds based on configured knowledge (prompts.yaml + knowledge files)
- **Spanish voseo required** — system prompt specifies Argentine Spanish ("podés", "te puedo", etc.)
- **Whapi webhook URLs** — Both `/webhook/messages` and `/v1/webhook/messages` are supported (Whapi changed paths)

---

## AgentKit System Instructions

The root `CLAUDE.md` file (46KB) contains AgentKit's **onboarding system instructions** for the `/build-agent` skill. That's used to guide users through building a NEW agent from scratch.

This file (`CLAUDE_DEV.md`) is for development and maintenance of THIS EXISTING agent.

If you need to rebuild the agent or change fundamental things, refer to the root `CLAUDE.md`. For day-to-day changes and improvements, use this file.

---

## Debugging

### Agent not responding

1. Check logs: `docker compose logs -f agent`
2. Test locally: `python tests/test_local.py`
3. Verify webhook URL in Whapi dashboard
4. Check `.env` has valid `ANTHROPIC_API_KEY` and `WHAPI_TOKEN`

### Agent giving wrong answers

1. Review `config/prompts.yaml` — system prompt defines what agent knows
2. Check conversation history in SQLite if needed: `sqlite3 agentkit.db`
3. Test with `python tests/test_local.py` to isolate issue

### Webhook errors

Check `agent/main.py` logging. The server logs raw payload and parsing errors.

---

## Next Steps for Improvement

- [ ] Add tool for querying appointment availability directly from COI system
- [ ] Implement ticket creation for complex inquiries
- [ ] Add metrics/analytics to track conversation types
- [ ] Migrate to PostgreSQL in production for better scaling
- [ ] Add handoff to human agents for out-of-scope questions
