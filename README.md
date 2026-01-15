# Meeting Safe

## 🚀 Live Demo

**Try it now:**
- [📅 Meeting Scheduler](https://meeting-safe-production.up.railway.app/app) — Schedule meetings with privacy-preserving coordination
- [🧠 Intelligence Dashboard](https://meeting-safe-production.up.railway.app/app/intelligence) — See how agents learn from user decisions

---

## The Challenge

> Meeting scheduling is a mostly solved problem when one person or agent has access to all calendars. It gets interesting when access is gated. Can you build an agentic system where each agent in the system only has access to the calendar of an individual, yet meetings are scheduled based on the availability of multiple people?
>
> The problem gets trickier when you start adding intelligence. I have meetings on my calendar I rarely attend. I'll reschedule internal 1:1s to make room for external customer calls. And everyone controls their own calendar in a slightly different way. How can a scheduling agent learn these preferences over time, instead of just looking for open slots, and possibly even escalate to me when needed.
>
> — [Distyl AI Engineering Challenge](https://www.linkedin.com/posts/aryeh-klein-670527150_following-up-from-my-post-yesterday-about-activity-7417579422553182208-SYgC?utm_source=share&utm_medium=member_desktop&rcm=ACoAABV47C0B2wge45FVCmyv3SKI6P84kfPHDcE)

---

## Two Problems

This challenge contains two distinct problems:

### Problem 1: Privacy
**How do you coordinate across calendars no one can see?**

Traditional schedulers (Calendly, x.ai) require a central system with access to everyone's availability. This leaks calendar data and enables inference attacks ("Free at 9?" "No." "10?" "No." ...).

### Problem 2: Intelligence  
**How do you schedule smarter than free/busy?**

Real calendars have nuance. Some meetings are sacred (customer calls), others are movable (team standups). A good scheduler learns these preferences instead of just finding empty slots.

---

## Two Solutions

### 🔒 Privacy Layer
Each agent scores time slots privately, then sends **hashes + scores** to a coordinator. The coordinator picks the best score without ever knowing what time it represents.

```
                    ┌─────────────────────────┐
                    │     Alice Agent         │
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
                   │ "abc1": 185           │
                   │ "k9p4": 240  ← BEST   │
                   │                       │
                   │ (has no idea what     │
                   │  these hashes mean!)  │
                   └───────────┬───────────┘
                               │
                   ⑤ Winner: "k9p4"
                               │
                               ▼
                   ┌───────────────────────┐
                   │     Alice Agent       │
                   │                       │
                   │ Decrypts: k9p4 = 11am │
                   │ Books the meeting! 📅 │
                   └───────────────────────┘
```

**Key insight:** The Meeting Agent can sum scores and pick winners—but only the organizer can decrypt the winning hash back to an actual time.

### 🧠 Intelligence Layer
Each agent uses an LLM to score slots based on:
- **Conflicts**: What's already scheduled
- **Importance**: Customer call vs team standup
- **Learned preferences**: "I always protect focus time"
- **Escalation**: Ask the user when uncertain

```
┌─────────────────────────────────────────────────────┐
│  Alice's Decision Matrix                            │
│  ─────────────────────────────────────────────────  │
│  Slot     │ Conflict        │ Decision    │ Score  │
│  ─────────────────────────────────────────────────  │
│  9:00 AM  │ Customer Call   │ PROTECT     │  10    │
│  10:00 AM │ Team Standup    │ RESCHEDULE  │  70    │
│  11:00 AM │ —               │ FREE        │  85    │
│  2:00 PM  │ Focus Time      │ PROTECT     │  20    │
└─────────────────────────────────────────────────────┘
```

---

## Two UIs

### [/app](https://meeting-safe-production.up.railway.app/app) — Privacy Layer
Watch hash-based coordination happen. See what the Meeting Agent sees (just hashes and scores).

### [/app/intelligence](https://meeting-safe-production.up.railway.app/app/intelligence) — Intelligence Layer  
Tabbed dashboard showing each user's decision matrix, learned preferences, and scoring breakdown.

---

## Quick Start

```bash
git clone https://github.com/arielwernick/meeting-safe.git
cd meeting-safe/prototype

python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows (or: source venv/bin/activate)
pip install -r requirements.txt

python seed.py  # Create sample data
python main.py  # Start server → http://localhost:8000/app
```

---

## Project Structure

```
meeting-safe/
├── prototype/
│   ├── main.py                   # FastAPI server
│   ├── agents/
│   │   ├── user_proxy_agent.py   # Private calendar + LLM scoring
│   │   ├── meeting_agent.py      # Hash-based coordination
│   │   └── hashing_agent.py      # Time slot obfuscation
│   └── static/
│       ├── index.html            # Privacy Layer UI
│       └── intelligence.html     # Intelligence Layer UI
├── docs/
│   ├── architecture.md
│   ├── security.md
│   └── intelligence.md
└── README.md
```

---

## The Solution

We solved both problems by keeping them separate:

1. **Privacy works without intelligence** — swap the LLM for a simple free/busy check, hashing still protects calendars
2. **Intelligence works without privacy** — disable hashing for internal use, smart scoring still helps
3. **Together they're powerful** — intelligent scores flow through private coordination

The two layers compose cleanly because each has one job.

---

MIT License
