# Meeting Safe 🔒

> Schedule meetings across multiple people without anyone seeing each other's calendars. Not even the scheduler.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## The Problem

**Traditional meeting schedulers see everything.** When you use Calendly, x.ai, or your company's scheduling tool, a central system has access to everyone's availability. It knows when you're free, when you're busy, and patterns emerge: "Alice is always in meetings on Tuesday afternoons." 

This is a privacy nightmare for sensitive organizations.

**Meeting Safe sees nothing but hashes** — yet still finds the perfect time.

```
Traditional Scheduler          Meeting Safe
─────────────────────         ─────────────
Alice: 9am ❌ 10am ✓          Alice: hash_01 → 85
Bob:   9am ✓ 10am ❌    vs    Bob:   hash_01 → 60
Carol: 9am ✓ 10am ✓          Carol: hash_01 → 40
                              
Knows: Everyone's calendar     Knows: Just scores
```

## How It Works (30 seconds)

1. **You want to schedule with Alice, Bob, Carol**
2. **Each person's agent scores time slots privately** — looking at their own calendar
3. **Scores are sent as hashes** — coordinator can't decode them to times  
4. **Best time selected** — only YOU (the organizer) learn what it is

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Alice Agent  │   │  Bob Agent   │   │ Carol Agent  │
│ (calendar 🔒)│   │ (calendar 🔒)│   │ (calendar 🔒)│
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │ hash→85          │ hash→60          │ hash→40
       └──────────────────┼──────────────────┘
                          ▼
              ┌───────────────────────┐
              │   Meeting Agent       │
              │ (sees hashes only 🙈) │
              └───────────┬───────────┘
                          │ winning hash
                          ▼
                   ┌─────────────┐
                   │  Organizer  │
                   │ (decrypts)  │
                   └─────────────┘
```

## Quick Start

```bash
git clone https://github.com/yourusername/meeting-safe.git
cd meeting-safe/prototype

# Setup (one time)
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt

# Run
python seed.py  # Create sample data
python main.py  # Start server
```

**Open http://localhost:8000/app** and schedule your first private meeting!

## What Makes This Different

### 🔒 Privacy by Design
Calendar data **never leaves** the user's agent. The coordinator sees utility scores attached to hashes—it can't map them back to times.

### 🛡️ Inference-Attack Resistant  
Traditional systems leak calendars through iteration ("Free at 9?" "No." "Free at 9:30?" "No." ...). We submit all slots simultaneously—no probing possible.

### 🧠 Intelligent, Not Just Available
The system learns your preferences:
- "Alice never reschedules customer calls"
- "Bob prefers mornings"
- "Carol will move team standups for external meetings"

### ⚡ Escalates When Uncertain
Instead of guessing wrong, Meeting Safe asks you when:
- Multiple times score similarly
- No good options exist
- It's a high-stakes meeting

## Project Structure

```
meeting-safe/
├── docs/
│   ├── architecture.md    # System design deep-dive
│   ├── security.md        # Threat model & attack resistance
│   └── intelligence.md    # LLM integration & learning
├── prototype/
│   ├── main.py            # FastAPI server
│   ├── agents/
│   │   ├── user_proxy_agent.py   # Private calendar + LLM scoring
│   │   ├── meeting_agent.py      # Hash-based coordination
│   │   └── hashing_agent.py      # SHA256 time obfuscation
│   ├── llm_service.py     # Mock LLM (swap to OpenAI)
│   └── static/index.html  # Demo UI
└── README.md
```

## The Demo

The prototype includes 3 users (Alice, Bob, Carol) with realistic calendars:

| User | Profile | Calendar |
|------|---------|----------|
| Alice | Busy executive | Customer calls, manager 1:1s, strategic meetings |
| Bob | Engineer | Focus time, standups, code reviews |
| Carol | PM | Cross-functional meetings, planning sessions |

Schedule a meeting and watch:
1. **Left panel**: Each user's calendar (private to them)
2. **Right panel**: What the Meeting Agent sees (just hashes!)
3. **Result**: Perfect time found, privacy preserved

## Deep Dive

| Document | What You'll Learn |
|----------|-------------------|
| [Architecture](docs/architecture.md) | Three-agent model, data flow, initiator-only decryption |
| [Security Model](docs/security.md) | Threat analysis, attack resistance, trust assumptions |
| [Intelligence](docs/intelligence.md) | LLM integration, learning from decisions, escalation logic |

## Using Real LLM

The prototype uses a deterministic mock LLM by default. To enable GPT-4:

```bash
# Create .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env
echo "LLM_MODE=openai" >> .env

# Restart server
python main.py
```

## Built For

This project demonstrates:
- **Multi-agent coordination** with clear trust boundaries
- **Privacy-preserving computation** via hash-based obfuscation
- **LLM-powered intelligence** that learns preferences
- **Security-first design** that blocks inference attacks

Originally built for [Distyl's AI Engineering hiring challenge](https://www.linkedin.com/posts/willcrichton_following-up-from-my-post-yesterday-about-activity-7285015651665965056-P0jL).

## License

MIT — build on it, improve it, make scheduling private everywhere.

---

<p align="center">
  <strong>Stop sharing your calendar with schedulers.</strong><br>
  Meeting Safe: Privacy-preserving scheduling for the rest of us.
</p>
