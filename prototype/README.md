# Prototype Implementation

This is the working prototype demonstrating the privacy-preserving scheduling architecture.

## Quick Start

```bash
# From meeting-safe/prototype directory
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

python seed.py  # Create sample users & calendars
python main.py  # Start server on http://localhost:8000
```

Open **http://localhost:8000/app** to use the demo.

## What's Implemented

| Feature | Status | Details |
|---------|--------|---------|
| Three-agent architecture | ✅ | User Proxy, Meeting Agent, Hashing Agent |
| Hash-based privacy | ✅ | SHA256 with meeting_id salt |
| Utility calculation | ✅ | Mock LLM with deterministic scoring |
| Learning/preferences | ✅ | Decision history recorded, applied to future |
| Escalation | ✅ | Triggers when scores too close |
| Web UI | ✅ | Shows calendars, agent view, results |

## Configuration

Copy `.env.example` to `.env` to configure:

```bash
LLM_MODE=mock     # or "openai" for real GPT-4
OPENAI_API_KEY=   # Required if LLM_MODE=openai
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server, all endpoints |
| `agents/user_proxy_agent.py` | Calendar access + utility calculation |
| `agents/meeting_agent.py` | Coordination logic (sees only hashes) |
| `agents/hashing_agent.py` | SHA256 time→hash conversion |
| `llm_service.py` | Mock LLM + OpenAI integration |
| `seed.py` | Sample data: Alice, Bob, Carol calendars |
| `static/index.html` | Single-page demo UI |

## API Reference

```
GET  /api/users                      # List all users
GET  /api/users/{id}/calendar        # Get user's calendar
GET  /api/users/{id}/decisions       # Learning history
POST /api/meetings/schedule          # Main scheduling flow
GET  /api/demo/naive-vs-intelligent  # Compare scheduling approaches
```

## Demo Users

| User | Role | Calendar Profile |
|------|------|------------------|
| Alice | Executive | Customer calls, manager 1:1s, packed schedule |
| Bob | Engineer | Focus time, standups, code reviews |
| Carol | PM | Cross-functional meetings, planning sessions |

See the [main README](../README.md) for architecture details.


- `GET /api/users` - List all users
- `GET /api/users/{id}/calendar` - Get user's calendar
- `GET /api/users/{id}/decisions` - Get learning history
- `POST /api/meetings/schedule` - Schedule a meeting (main flow)
