# Meeting Safe Prototype

Privacy-preserving multi-agent meeting scheduler.

## Quick Start

```bash
cd prototype

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Seed the database
python seed.py

# Run the server
python main.py
```

Then open: **http://localhost:8000/app**

## What It Demonstrates

1. **Gated Access**: Each User Proxy Agent only sees its own calendar
2. **Privacy via Hashing**: Meeting Agent sees hashes, never times
3. **LLM Intelligence**: Smart scheduling (currently mocked, swap to real LLM)
4. **Learning**: Records decisions and applies preferences to future scheduling
5. **Escalation**: Asks user when uncertain

## Using Real LLM

1. Copy `.env.example` to `.env`
2. Add your OpenAI API key
3. Set `LLM_MODE=openai`
4. Restart the server

## Project Structure

```
prototype/
├── main.py              # FastAPI server
├── config.py            # Configuration (API keys, etc.)
├── models.py            # Pydantic models
├── database.py          # SQLite database
├── seed.py              # Sample data
├── llm_service.py       # LLM integration (mock + OpenAI)
├── agents/
│   ├── hashing_agent.py    # Cryptographic hashing
│   ├── meeting_agent.py    # Coordination logic
│   └── user_proxy_agent.py # Individual calendar + utilities
└── static/
    └── index.html       # Demo UI
```

## API Endpoints

- `GET /api/users` - List all users
- `GET /api/users/{id}/calendar` - Get user's calendar
- `GET /api/users/{id}/decisions` - Get learning history
- `POST /api/meetings/schedule` - Schedule a meeting (main flow)
