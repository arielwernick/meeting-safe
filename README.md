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
2. **Your agent creates an event with possible time slots, each slot gets a hashed ID**
3. **Each attendee's agent receives the hash→time mapping, scores each slot privately**
4. **Attendees send back only hashes + scores** — the Meeting Agent never sees actual times
5. **Best hash wins** — your agent decrypts it back to the actual time

```
                    ┌─────────────────────────┐
                    │     Your Agent          │
                    │  (creates the meeting)  │
                    └───────────┬─────────────┘
                                │
                    ① Create event with slots:
                       9am, 10am, 11am
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    Hashing Service      │
                    │  9am  → "x7f2"          │
                    │  10am → "abc1"          │
                    │  11am → "k9p4"          │
                    └───────────┬─────────────┘
                                │
                    ② Send hash↔time map to attendees
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ Alice Agent  │        │  Bob Agent   │        │ Carol Agent  │
│ (calendar 🔒)│        │ (calendar 🔒)│        │ (calendar 🔒)│
│              │        │              │        │              │
│ Decodes map, │        │ Decodes map, │        │ Decodes map, │
│ checks own   │        │ checks own   │        │ checks own   │
│ calendar     │        │ calendar     │        │ calendar     │
└──────┬───────┘        └──────┬───────┘        └──────┬───────┘
       │                       │                       │
       │ ③ Send scores         │                       │
       │ (hashes only!)        │                       │
       │                       │                       │
       │ "x7f2": 30            │ "x7f2": 50            │ "x7f2": 20
       │ "abc1": 85            │ "abc1": 60            │ "abc1": 40
       │ "k9p4": 70            │ "k9p4": 80            │ "k9p4": 90
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               ▼
                   ┌───────────────────────┐
                   │    Meeting Agent      │
                   │                       │
                   │ ④ Sums scores:        │
                   │ "x7f2": 100           │
                   │ "abc1": 185  ← BEST   │
                   │ "k9p4": 240           │
                   │                       │
                   │ (has no idea what     │
                   │  these hashes mean!)  │
                   └───────────┬───────────┘
                               │
                   ⑤ Winner: "k9p4"
                               │
                               ▼
                   ┌───────────────────────┐
                   │     Your Agent        │
                   │                       │
                   │ Decrypts: k9p4 = 11am │
                   │ Books the meeting! 📅 │
                   └───────────────────────┘
```

**The privacy guarantee:** The Meeting Agent orchestrates everything but only ever sees opaque hashes like "abc1". It can do math, pick winners—but never knows it just scheduled an 11am meeting.

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

**Open http://localhost:8000/app** and explore the two-layer system!

---

## Two Layers, One System

Meeting Safe separates two hard problems into distinct, composable layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LAYER                           │
│   Each user's agent reasons about THEIR calendar privately      │
│   • LLM scores slots based on context + learned preferences     │
│   • Knows: "I reschedule standups for customer calls"           │
│   • Escalates when uncertain                                    │
│   • Output: scores per time slot                                │
└─────────────────────────────────────────────────────────────────┘
                              │ scores
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PRIVACY LAYER                               │
│   Coordination happens WITHOUT revealing calendars              │
│   • Hash-based slot IDs hide actual times                       │
│   • Meeting Agent only sees hashes + scores                     │
│   • Only organizer can decrypt the winning slot                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why separate them?**
- You could swap the LLM for a dumb "free/busy" checker — privacy still works
- You could disable hashing for internal use — intelligence still works
- Each layer has ONE job, making it easier to understand, test, and trust

---

## The Demo: Two Views

### 📅 View 1: Scheduling (Privacy Layer)
`http://localhost:8000/app`

Watch the hash-based coordination in real-time:
- **Left panel**: User calendars (private to each agent)
- **Right panel**: What the Meeting Agent sees (just hashes!)
- **Result**: Meeting scheduled, privacy preserved

### 🧠 View 2: Intelligence Dashboard
`http://localhost:8000/app/intelligence`

Explore how each agent makes decisions — tabbed like Excel workbooks:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Alice]  [Bob]  [Carol]                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alice's Decision Matrix                                        │
│  ───────────────────────────────────────────────────────────── │
│  Slot      │ Base │ Conflict    │ Preference │ Final │ Reason  │
│  ───────────────────────────────────────────────────────────── │
│  9:00 AM   │  50  │ -30 (1:1)   │ +10 (AM)   │  30   │ Has 1:1 │
│  10:00 AM  │  50  │ -80 (cust)  │ +10 (AM)   │ -20   │ Customer│
│  11:00 AM  │  50  │  0          │ -5 (lunch) │  45   │ Open    │
│  2:00 PM   │  50  │ -20 (team)  │ +15 (pref) │  45   │ Movable │
│  3:00 PM   │  50  │  0          │ +20 (peak) │  70   │ ⭐ Best │
│                                                                 │
│  Learned Preferences:                                           │
│  • Never reschedule: Customer calls, Board meetings             │
│  • Will reschedule: Team syncs, Internal 1:1s                   │
│  • Peak productivity: 2-4pm                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Click any user tab to see:
- **Decision matrix**: How each slot was scored (base, conflicts, preferences)
- **Learned preferences**: What patterns the agent has learned
- **Recent decisions**: History of escalations and overrides

---

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
│   └── static/
│       ├── index.html            # Scheduling UI (Privacy Layer)
│       └── intelligence.html     # Decision Matrix UI (Intelligence Layer)
└── README.md
```

## Sample Users

The prototype includes 3 users (Alice, Bob, Carol) with realistic calendars:

| User | Profile | Calendar Style | Reschedulability |
|------|---------|----------------|------------------|
| Alice | Executive | Customer calls, manager 1:1s | Never moves customer calls |
| Bob | Engineer | Focus time, standups | Protects deep work time |
| Carol | PM | Cross-functional syncs | Flexible with internal meetings |

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
