# Meeting Safe

A privacy-preserving multi-agent meeting scheduler. Each agent only has access to individual calendar data, yet meetings are scheduled across multiple people without exposing private availability information.

## 🔒 Privacy Model

Unlike traditional schedulers that see everyone's calendars, Meeting Safe uses a three-agent architecture:

- **User Proxy Agents** - Each user has their own agent that sees ONLY their calendar
- **Meeting Agent** - Coordinates scheduling by seeing only hashed time slots and utility scores (never raw times or calendar data)
- **Hashing Agent** - Converts times to hashes, ensuring the Meeting Agent can't learn availability patterns

## 🧠 Intelligence

The system uses LLMs to:
- Calculate utility scores based on calendar conflicts and learned preferences
- Recommend whether to reschedule existing events for new meetings
- Learn from user decisions over time (e.g., "Alice never reschedules 1:1s with her manager")

## 🚀 Quick Start

```bash
cd prototype

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Seed sample data
python seed.py

# Run server
python main.py
```

Then open http://localhost:8000/app

## 📁 Project Structure

```
prototype/
├── main.py              # FastAPI server
├── database.py          # SQLite + SQLAlchemy models
├── models.py            # Pydantic request/response models
├── seed.py              # Sample data generator
├── agents/
│   ├── user_proxy_agent.py   # Per-user calendar + LLM integration
│   ├── meeting_agent.py      # Coordination (sees only hashes)
│   └── hashing_agent.py      # SHA256 time hashing
├── llm_service.py       # Mock LLM + OpenAI integration
└── static/
    └── index.html       # Web UI
```

## 🎯 Key Features

- **Privacy by Design** - Meeting Agent never sees actual times or calendar contents
- **Escalation** - When multiple times score similarly, user chooses
- **Learning** - System remembers which event types users protect vs. reschedule
- **Mock LLM** - Works without API keys; swap in OpenAI for production

## 📄 License

MIT
