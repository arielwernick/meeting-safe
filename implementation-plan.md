# Implementation Plan

## Goal
Working prototype that demonstrates:
1. ✅ Gated access (each agent sees only one calendar)
2. ✅ Multi-party scheduling via hashes
3. ✅ LLM-based intelligence (not just open slots)
4. ✅ Learning from user behavior
5. ✅ Escalation when uncertain
6. 🎯 **Preference Explainability** — Show HOW preferences affect decisions

---

## What Makes This Project Stand Out

The original problem asks: *"How can a scheduling agent learn these preferences over time?"*

Most scheduling demos just show the **output** (a scheduled meeting). We go further by showing:

1. **The WHY**: Explain each scoring decision with visible reasoning
2. **The LEARNING**: Show preferences being applied in real-time
3. **The TRADEOFFS**: Visualize what the agent considered rescheduling
4. **The ESCALATION**: Demonstrate uncertainty → human-in-the-loop

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  - 3 calendar views (Alice, Bob, Carol)                          │
│  - Meeting request form                                          │
│  - "What Meeting Agent sees" panel (hashes only)                 │
│  - Escalation modal                                              │
│  - Decision history log                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                         │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Alice Agent │  │ Bob Agent   │  │ Carol Agent │              │
│  │ - calendar  │  │ - calendar  │  │ - calendar  │              │
│  │ - prefs     │  │ - prefs     │  │ - prefs     │              │
│  │ - history   │  │ - history   │  │ - history   │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│                 ┌─────────────────┐                              │
│                 │  Meeting Agent  │                              │
│                 │  (sees hashes)  │                              │
│                 └────────┬────────┘                              │
│                          │                                       │
│                          ▼                                       │
│                 ┌─────────────────┐                              │
│                 │  Hashing Agent  │                              │
│                 │  (stateless)    │                              │
│                 └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE                                  │
│  - calendars (per user)                                          │
│  - decision_history (per user)                                   │
│  - meetings (scheduled)                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Calendar Event
```python
class CalendarEvent:
    id: str
    user_id: str
    title: str
    start_time: datetime
    end_time: datetime
    event_type: str        # "customer_call", "internal_1on1", "team_meeting", etc.
    external: bool
    importance: int        # 1-10
    recurring: bool
```

### Meeting Request
```python
class MeetingRequest:
    id: str
    title: str
    organizer_id: str
    participant_ids: list[str]
    duration_minutes: int
    window_start: datetime
    window_end: datetime
    meeting_type: str
    external: bool
```

### Decision History (for learning)
```python
class SchedulingDecision:
    id: str
    user_id: str
    timestamp: datetime
    meeting_request_id: str
    recommended_slot: datetime
    recommended_action: str     # "schedule", "reschedule_existing"
    conflicting_event_type: str # What would be displaced
    user_action: str            # "accepted", "rejected", "modified"
    final_slot: datetime
```

### Utility Response
```python
class UtilityResponse:
    user_id: str
    utilities: dict[str, int]   # hash -> score
    escalate: bool
    escalation_reason: str
```

---

## API Endpoints

### User Proxy Agent APIs
```
POST /users/{user_id}/calendar          # Add event
GET  /users/{user_id}/calendar          # View calendar
GET  /users/{user_id}/preferences       # Get learned preferences
POST /users/{user_id}/utilities         # Calculate utilities for hashes
POST /users/{user_id}/decision          # Record user decision (for learning)
```

### Meeting Agent APIs  
```
POST /meetings/request                  # Initiate scheduling
GET  /meetings/{meeting_id}/status      # Check status
POST /meetings/{meeting_id}/resolve     # User resolves escalation
```

### Hashing Agent APIs
```
POST /hash/generate                     # Generate hashes for time slots
```

---

## Core Flows

### Flow 1: Schedule a Meeting (Happy Path)
```
1. Frontend: Alice submits meeting request with Bob, Carol
2. Meeting Agent: Generate all time slots in window
3. Hashing Agent: Hash each slot, return hashes to Meeting Agent, mapping to User Agents
4. User Agents (parallel): 
   - Receive hashes + mapping
   - Calculate utilities via LLM
   - Return {hash: utility}
5. Meeting Agent: Aggregate utilities, find winner
6. Meeting Agent: Return winning hash to Alice's Agent only
7. Alice's Agent: Decrypt hash, create calendar invites
8. Frontend: Show "Meeting scheduled for [time]"
```

### Flow 2: Escalation (Low Confidence)
```
1-4. Same as above
5. Alice's Agent: Utilities show no good options (all < 50) or tie
6. Alice's Agent: Return escalate=true with top options
7. Frontend: Show escalation modal with choices
8. User: Picks an option
9. Record decision in history (for learning)
10. Continue with selected slot
```

### Flow 3: Learning in Action
```
1. User schedules meeting, LLM recommends slot A
2. User overrides, picks slot B instead
3. System records: "User rejected rescheduling manager 1:1"
4. Next scheduling request:
   - LLM prompt includes: "User previously rejected rescheduling manager 1:1s"
   - LLM now avoids suggesting slots that conflict with manager 1:1s
5. Frontend shows: "Learned preference applied"
```

---

## LLM Integration

### Single Prompt Template
```
You are a scheduling assistant for {user_name}.

NEW MEETING REQUEST:
- Title: {title}
- Organizer: {organizer}
- Type: {meeting_type}
- External: {external}
- Duration: {duration} minutes

YOUR CALENDAR FOR EACH TIME SLOT:
{for each slot}
- {time}: {status} 
  {if conflict: "Conflict: {event_title} ({event_type}, importance {importance})"}
{end for}

LEARNED PREFERENCES:
{for each preference in history}
- {preference_description}
{end for}

INSTRUCTIONS:
For each time slot, output a utility score 0-100.
- 100 = perfect slot (free, preferred time)
- 70-99 = good slot (free, acceptable time)
- 40-69 = willing to reschedule existing meeting for this
- 1-39 = reluctant but possible
- 0 = absolutely not (important conflict, external meeting, etc.)

Consider:
- User's learned preferences
- Meeting importance (external > internal usually)
- Existing meeting importance
- Time of day preferences

Output JSON only:
{
  "utilities": {"hash_001": score, "hash_002": score, ...},
  "reasoning": "brief explanation"
}
```

---

## Database Schema

```sql
-- Users
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL
);

-- Calendar Events
CREATE TABLE calendar_events (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    title VARCHAR NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    event_type VARCHAR,
    external BOOLEAN DEFAULT FALSE,
    importance INTEGER DEFAULT 5,
    recurring BOOLEAN DEFAULT FALSE
);

-- Decision History (for learning)
CREATE TABLE decision_history (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    meeting_type VARCHAR,
    conflicting_type VARCHAR,
    recommended_action VARCHAR,
    user_action VARCHAR,  -- 'accepted', 'rejected', 'modified'
    notes TEXT
);

-- Meetings (scheduled)
CREATE TABLE meetings (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    organizer_id VARCHAR REFERENCES users(id),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR DEFAULT 'pending'
);

-- Meeting Participants
CREATE TABLE meeting_participants (
    meeting_id VARCHAR REFERENCES meetings(id),
    user_id VARCHAR REFERENCES users(id),
    role VARCHAR,  -- 'organizer', 'required', 'optional'
    PRIMARY KEY (meeting_id, user_id)
);
```

---

## Implementation Phases

### Phase 1: Core Infrastructure ✅ COMPLETE
- [x] Project setup (FastAPI + SQLite)
- [x] Database schema + seed data (3 users, sample calendars)
- [x] Basic API endpoints
- [x] Hashing agent (SHA256)

### Phase 2: Scheduling Flow ✅ COMPLETE
- [x] Meeting Agent coordination logic
- [x] User Proxy Agent utility calculation (mock + real LLM)
- [x] Aggregation + winner selection
- [x] Frontend: meeting request form + calendar views

### Phase 3: Intelligence ✅ COMPLETE
- [x] LLM integration for utility calculation
- [x] Decision history storage
- [x] Preference extraction from history
- [x] Include preferences in LLM prompt

### Phase 4: Demo Polish 🔄 IN PROGRESS
- [x] "What Meeting Agent sees" panel (show only hashes)
- [x] Escalation modal
- [ ] Learning visualization ("Applied 3 learned preferences")
- [ ] Side-by-side comparison (naive vs intelligent scheduling)

### Phase 5: Preference Explainability 🎯 NEW - The Differentiator
- [ ] **Decision Breakdown Panel** — Show per-slot reasoning
- [ ] **Preference Influence Visualization** — "This scored 65 because you protected manager_1on1 before"
- [ ] **Before/After Learning Demo** — Toggle to show how learning changes outcomes
- [ ] **Conflict Trade-off View** — "Would reschedule: Team Standup (importance 5)"

---

## Preference Explainability Design

### What We're Demonstrating

The problem statement specifically asks about showing how the agent **learns preferences**. Most demos just show "meeting scheduled" — we show the *reasoning*.

### Key UI Components

#### 1. Decision Reasoning Panel
```
┌─────────────────────────────────────────────────────┐
│ 🧠 How Alice's Agent Scored This Slot               │
├─────────────────────────────────────────────────────┤
│ Slot: 10:00 AM                                      │
│ Base Score: 0 (CONFLICT)                            │
│                                                     │
│ Conflict: "Customer Call - Acme Corp"               │
│   • Type: customer_call                             │
│   • Importance: 9/10                                │
│   • External: YES ⛔                                │
│                                                     │
│ Decision: PROTECT (score: 0)                        │
│   → "Never reschedule external customer calls"      │
├─────────────────────────────────────────────────────┤
│ Slot: 9:00 AM                                       │
│ Base Score: 0 (CONFLICT)                            │
│                                                     │
│ Conflict: "Team Standup"                            │
│   • Type: team_meeting                              │
│   • Importance: 5/10                                │
│   • External: NO                                    │
│                                                     │
│ Learned Preference Applied: ✅                      │
│   → "User previously ACCEPTED rescheduling          │
│      team_meeting for customer_call"                │
│                                                     │
│ Decision: WILLING TO RESCHEDULE (score: 65)         │
└─────────────────────────────────────────────────────┘
```

#### 2. Learning Applied Indicator
```
┌─────────────────────────────────────────────────────┐
│ 📚 Preferences Applied This Request                 │
├─────────────────────────────────────────────────────┤
│ ✓ Protect manager_1on1 (rejected 3 days ago)        │
│ ✓ Reschedule team_meeting for external (accepted)   │
│ ✓ Morning slots preferred (9-11 AM +10 bonus)       │
└─────────────────────────────────────────────────────┘
```

#### 3. Before/After Toggle
```
┌───────────────────────────────────────────────────────────────┐
│ Compare: [ ] Naive Mode  [●] Learning Mode                    │
├───────────────────────────────────────────────────────────────┤
│ Naive Mode (just checks busy/free):                           │
│   • 9:00 AM: BUSY ❌                                          │
│   • 10:00 AM: BUSY ❌                                         │
│   • 2:00 PM: FREE ✓  ← Would pick this (lunch hour!)          │
│                                                               │
│ Learning Mode (our system):                                   │
│   • 9:00 AM: Score 65 ← Willing to move standup               │
│   • 10:00 AM: Score 0 ← Protects customer call                │
│   • 2:00 PM: Score 70 ← Free but lunch penalty                │
│   Winner: 9:00 AM (moves low-importance standup)              │
└───────────────────────────────────────────────────────────────┘
```

### API Response Enhancement

Current response:
```json
{
  "utilities": {"hash_abc": 65, "hash_def": 0},
  "reasoning": "Standard availability scoring"
}
```

Enhanced response:
```json
{
  "utilities": {"hash_abc": 65, "hash_def": 0},
  "reasoning": "Willing to reschedule team_meeting; protecting customer_call",
  "slot_breakdown": [
    {
      "hash": "hash_abc",
      "time": "9:00",
      "score": 65,
      "base_score": 0,
      "status": "conflict",
      "conflict": {
        "title": "Team Standup",
        "event_type": "team_meeting",
        "importance": 5,
        "external": false
      },
      "factors": [
        {"type": "conflict_penalty", "value": -80, "reason": "Existing meeting"},
        {"type": "reschedule_willingness", "value": +60, "reason": "Low importance internal"},
        {"type": "learned_preference", "value": +5, "reason": "Previously accepted rescheduling team_meeting"}
      ],
      "decision": "WILLING_TO_RESCHEDULE",
      "decision_reason": "Internal meeting with importance 5, user has accepted similar rescheduling before"
    }
  ],
  "preferences_applied": [
    {"preference": "protect_manager_1on1", "source": "User rejected rescheduling on Jan 12"},
    {"preference": "reschedule_team_meeting", "source": "User accepted rescheduling on Jan 10"}
  ]
}
```

---

## Demo Script (2 minutes)

### Scene 1: The Privacy Problem (20s)
"Traditional schedulers see everyone's calendar. Watch what our Meeting Agent sees..."
→ Show hashes panel: just `hash_a3f2...`, `hash_b7c1...`

### Scene 2: Basic Scheduling (30s)  
"Alice wants to meet Bob and Carol. Each agent scores slots privately."
→ Show utilities flowing in
→ Meeting scheduled at optimal time

### Scene 3: Intelligence — The Differentiator (45s)
"But I have a customer call at 2pm. A naive system would just say 'busy'."
→ Click "Compare" to show Naive vs Intelligent side-by-side
→ Show LLM reasoning: "Willing to reschedule internal standup (utility 65)"
→ Point to "🧠 How Preferences Affected This Decision" panel
→ Show each slot's factors: importance, learned preferences, time-of-day bonuses

### Scene 4: Learning in Action (30s)
"What if I reject that suggestion?"
→ Override the recommendation in escalation modal
→ Show decision recorded in "Learned Preferences" panel
→ "Next time, system remembers: Alice protects standups"

### Scene 5: Escalation (15s)
"When uncertain, it asks — and learns from your choice."
→ Show escalation modal with scored options
→ User picks, preference recorded

---

## Current Implementation Status

### ✅ Fully Implemented
- Privacy-preserving hashing architecture
- Multi-agent coordination (Meeting Agent, User Proxy Agents, Hashing Agent)
- LLM-based utility calculation (mock + OpenAI)
- Decision history storage and preference learning
- Escalation detection and user choice modal
- **NEW: Rich explainability showing preference factors**
- **NEW: Naive vs Intelligent comparison endpoint**
- **NEW: Slot-by-slot decision reasoning UI**

### 🔧 Architecture (Actual)
```
meeting-safe/prototype/
├── main.py                     # FastAPI app with all endpoints
├── config.py                   # Configuration (API keys, modes)
├── database.py                 # SQLAlchemy models + DB setup
├── models.py                   # Pydantic models
├── llm_service.py              # LLM integration (mock + OpenAI)
├── seed.py                     # Sample data generator
├── agents/
│   ├── meeting_agent.py        # Coordinates scheduling
│   ├── user_proxy_agent.py     # Per-user private agent
│   └── hashing_agent.py        # Stateless hash generation
└── static/
    └── index.html              # Single-page frontend (vanilla JS)
```

---

## Tech Stack (Final)

### Chosen: Local Python + SQLite
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Vanilla HTML/JS + TailwindCSS (CDN)
- **LLM**: Pluggable (MockLLM for demos, OpenAI for production)

### Why This Works
1. **Zero deployment friction** — run `python main.py` and it works
2. **Single HTML file** — easy to understand, no build step
3. **LLM mode toggle** — demo without API keys, switch to real AI easily
4. **Complete in one repo** — everything self-contained for evaluation

---

## What Makes This Project Stand Out (Summary)

### 1. Privacy-Preserving Architecture
- Meeting Agent never sees raw calendars
- Hash-based coordination protects sensitive data
- Each user's preferences stay private

### 2. Intelligent Decision-Making (Not Just Busy/Free)
- Considers meeting importance, type, and external status
- Learns from user behavior (accepts/rejects)
- Makes smart tradeoff decisions

### 3. Explainable AI — **The Key Differentiator**
- Shows EXACTLY why each slot scored the way it did
- Visualizes which learned preferences were applied
- Compares naive vs intelligent scheduling side-by-side

### 4. Human-in-the-Loop
- Escalates when uncertain (ties, low scores)
- Records user choices for future learning
- Transparent about what it learned

---

## Running the Demo

```bash
cd prototype
python seed.py        # Create sample data
python main.py        # Start server on http://127.0.0.1:8000
```

Then open `http://127.0.0.1:8000/app` in your browser.

### Demo Flow
1. View the 3 users' calendars (Alice, Bob, Carol)
2. Create a meeting request
3. Watch the hashes + utilities in "Meeting Agent View"
4. Click "Compare" to see Naive vs Intelligent scheduling
5. If escalation needed, pick an option and see it learned
6. Check "🧠 How Preferences Affected This Decision" panel
