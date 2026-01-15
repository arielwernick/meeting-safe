# Implementation Plan

## Goal
Working prototype that demonstrates:
1. ✅ Gated access (each agent sees only one calendar)
2. ✅ Multi-party scheduling via hashes
3. ✅ LLM-based intelligence (not just open slots)
4. ✅ Learning from user behavior
5. ✅ Escalation when uncertain

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

### Phase 1: Core Infrastructure (2-3 hours)
- [ ] Project setup (FastAPI + React)
- [ ] Database schema + seed data (3 users, sample calendars)
- [ ] Basic API endpoints
- [ ] Hashing agent (simple SHA256)

### Phase 2: Scheduling Flow (2-3 hours)
- [ ] Meeting Agent coordination logic
- [ ] User Proxy Agent utility calculation (mock first, then LLM)
- [ ] Aggregation + winner selection
- [ ] Frontend: meeting request form + calendar views

### Phase 3: Intelligence (2-3 hours)
- [ ] LLM integration for utility calculation
- [ ] Decision history storage
- [ ] Preference extraction from history
- [ ] Include preferences in LLM prompt

### Phase 4: Demo Polish (1-2 hours)
- [ ] "What Meeting Agent sees" panel (show only hashes)
- [ ] Escalation modal
- [ ] Learning visualization ("Applied 3 learned preferences")
- [ ] Side-by-side comparison (naive vs intelligent scheduling)

---

## Demo Script (2 minutes)

### Scene 1: The Privacy Problem (20s)
"Traditional schedulers see everyone's calendar. Watch what our Meeting Agent sees..."
→ Show hashes panel: just `hash_a3f2...`, `hash_b7c1...`

### Scene 2: Basic Scheduling (30s)  
"Alice wants to meet Bob and Carol. Each agent scores slots privately."
→ Show utilities flowing in
→ Meeting scheduled at optimal time

### Scene 3: Intelligence (40s)
"But I have a customer call at 2pm. A naive system would just say 'busy'."
→ Show LLM reasoning: "Willing to reschedule internal standup (utility 65)"
→ Meeting scheduled by intelligently moving the standup

### Scene 4: Learning (30s)
"What if I reject that suggestion?"
→ Override the recommendation
→ Show decision recorded
→ "Next time, system remembers: Alice protects standups"

### Scene 5: Escalation (20s)
"When uncertain, it asks."
→ Show escalation modal with options
→ User picks, preference learned

---

## File Structure

```
meeting-safe/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── agents/
│   │   ├── user_proxy.py       # User Proxy Agent
│   │   ├── meeting.py          # Meeting Agent
│   │   └── hashing.py          # Hashing Agent
│   ├── models/
│   │   ├── calendar.py
│   │   ├── meeting.py
│   │   └── decision.py
│   ├── llm/
│   │   └── scheduler.py        # LLM prompt + parsing
│   └── db/
│       ├── database.py
│       └── seed.py             # Sample data
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── CalendarView.tsx
│   │   │   ├── MeetingForm.tsx
│   │   │   ├── HashesPanel.tsx
│   │   │   ├── EscalationModal.tsx
│   │   │   └── LearningLog.tsx
│   │   └── api/
│   │       └── client.ts
│   └── package.json
└── README.md
```

---

## Tech Stack Decision

### Option A: Local Python + SQLite
**Pros:**
- Fast iteration
- No deployment complexity
- Easy to demo locally
- Full control

**Cons:**
- Need to run locally for demo
- No shareable link

### Option B: Vercel + Neon
**Pros:**
- Shareable demo URL
- "Production-like" setup
- Can include in portfolio

**Cons:**
- Deployment overhead
- Serverless constraints
- Need to manage secrets

**Recommendation:** Start with **Local Python** for speed, then deploy to Vercel once working.
