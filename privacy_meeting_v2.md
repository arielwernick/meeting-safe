# Privacy-Preserving Multi-Agent Meeting Scheduling: Final Design

## Executive Summary

**The Problem**: How do we schedule meetings across multiple participants when each person controls their own calendar and we cannot trust a central coordinator with access to everyone's availability data?

**The Solution**: A three-agent architecture where User Proxy Agents calculate availability privately, a Hashing Agent provides cryptographic privacy through deterministic hashing, and a Meeting Agent coordinates scheduling without ever seeing raw calendar data or even learning the final scheduled time.

**Key Insight**: The meeting initiator (organizer) is the only party who needs to know the final scheduled time. They decrypt the winning hash and send calendar invites directly to participants, eliminating the need for the Meeting Agent to ever learn sensitive information.

---

## Part 1: The Complete Problem

### 1.1 The Meeting Scheduling Challenge

Meeting scheduling seems simple on the surface: find a time when everyone is available. But the problem becomes complex when we introduce realistic constraints:

**Constraint 1: Privacy**
Each person controls their own calendar. Alice doesn't want to reveal her full schedule to Bob. Bob doesn't want a central coordinator to know his availability patterns. The system should preserve calendar privacy while still enabling coordination.

**Constraint 2: Gated Access**
In many organizational contexts, no single entity has access to all calendars. Alice's calendar is managed by her agent. Bob's calendar is managed by his agent. There's no central calendar database. The scheduling system must work across these boundaries.

**Constraint 3: Inference Attacks**
Even if we hide raw calendar data, a malicious coordinator could infer availability by asking sequential questions: "Are you free at 9 AM?" "Are you free at 9:30 AM?" By collecting yes/no responses, the coordinator reconstructs the entire calendar without ever seeing the raw data.

**Constraint 4: Intelligent Rescheduling**
Real-world scheduling isn't just about finding open slots. People have preferences: they'll reschedule internal 1:1s for customer calls, but not vice versa. They prefer certain times of day. The system should learn these patterns and make intelligent rescheduling decisions.

**Constraint 5: Hierarchical Priorities**
Not all participants are equal. A meeting organizer has more authority than an optional attendee. The system should respect this hierarchy when making scheduling decisions.

### 1.2 Why Existing Solutions Fail

**Solution 1: Centralized Coordinator (Naive)**
```
Coordinator has access to all calendars
→ Coordinator finds optimal time
→ Meeting scheduled

Problem: Coordinator knows everything about everyone's availability.
Privacy nightmare for organizations with sensitive schedules.
```

**Solution 2: Distributed Polling (Sequential)**
```
Meeting Agent asks: "Are you free at 9 AM?"
Alice's Agent: "No"
Meeting Agent asks: "Are you free at 9:30 AM?"
Alice's Agent: "Yes"
...

Problem: By collecting sequential responses, Meeting Agent reconstructs 
Alice's entire calendar without ever seeing raw data. Inference attack.
```

**Solution 3: Central Decryption (State Accumulation)**
```
User Proxy Agents encrypt their availability
Meeting Agent aggregates
Central service decrypts winning time
→ Tells everyone the scheduled time

Problem: Central decryption service accumulates knowledge about 
scheduled times across all meetings. Can build user profiles over time.
```

### 1.3 The Core Insight

The real problem isn't hiding individual data points—it's preventing correlation attacks and eliminating unnecessary central knowledge.

We need a system where:
1. **No sequential queries** - All time slots are presented simultaneously
2. **No time-to-utility mapping visible to coordinator** - Meeting Agent sees hashes, not times
3. **No coordinator knowledge of final time** - Coordinator never needs to know outcome
4. **Deterministic hashing** - All users hash the same time to the same hash (for intersection)
5. **Stateless privacy layer** - The privacy mechanism doesn't accumulate knowledge
6. **Distributed decryption** - Only initiator needs to decrypt

---

## Part 2: Our Architectural Solution

### 2.1 Three-Agent Architecture

We solve this with three specialized agents, each with a single responsibility:

#### **Agent 1: User Proxy Agent** (Runs locally on user's machine)
- **Responsibility**: Knows the user's calendar and preferences
- **Input**: Meeting request with scheduling window and hashes
- **Process**: 
  1. Receives hash→time mapping from Hashing Agent
  2. Calculates utility score for each time based on calendar (0-100)
  3. Maps utilities to hashes
  4. Sends only non-zero hash/utility pairs to Meeting Agent
  5. If initiator: receives winning hash, decrypts to time, sends invites
  6. If participant: receives calendar invite from initiator
- **Output**: Hash/utility pairs (never sends raw times to Meeting Agent)
- **Privacy**: Calendar never leaves the user's agent

#### **Agent 2: Meeting Agent** (Runs in coordination service)
- **Responsibility**: Coordinates scheduling across all participants
- **Input**: Meeting request, hash/utility pairs from all User Proxy Agents
- **Process**:
  1. Generates all possible times in scheduling window
  2. Sends times to Hashing Agent for hashing
  3. Receives hashes from Hashing Agent (NOT the mapping)
  4. Distributes hashes to all User Proxy Agents
  5. Collects hash/utility pairs from all agents
  6. Buckets utilities by hash
  7. Applies importance weights (initiator > required > optional)
  8. Aggregates to find winning hash
  9. Sends winning hash ONLY to initiating User Proxy Agent
  10. Job complete - never learns the scheduled time
- **Output**: Winning hash (to initiator only)
- **Privacy**: Never sees raw calendar data, never sees hash→time mapping, never learns scheduled time

#### **Agent 3: Hashing Agent** (Stateless cryptographic service)
- **Responsibility**: Provides cryptographic privacy through deterministic hashing
- **Input**: Meeting_id + list of all possible times
- **Process**:
  1. For each time: `hash = SHA256(meeting_id || time)`
  2. Sends list of hashes to Meeting Agent (no mapping)
  3. Sends full hash→time mapping to each User Proxy Agent
  4. Immediately deletes all state
- **Output**: Hashes to Meeting Agent, full mapping to User Agents
- **Privacy**: Stateless; cannot correlate across users or meetings

### 2.2 Data Flow: Complete Example

```
PHASE 0: MEETING CREATION

Alice wants to schedule a customer call with Bob and Carol.

Alice's Agent → Meeting Agent:
{
  meeting_id: "mtg_123",
  initiator: "alice",
  title: "Customer Call",
  participants: [
    {id: "alice", role: "host", importance: "mandatory"},
    {id: "bob", role: "attendee", importance: "required"},
    {id: "carol", role: "attendee", importance: "optional"}
  ],
  scheduling_window: {
    earliest: "2026-01-16 09:00",
    latest: "2026-01-16 17:00",
    slot_duration: 30
  }
}

---

PHASE 1: HASH GENERATION

Meeting Agent generates all possible times:
times = [
  "2026-01-16 09:00",
  "2026-01-16 09:30",
  "2026-01-16 10:00",
  "2026-01-16 10:30",
  ...
  "2026-01-16 16:30"
]
// Total: 16 slots

Meeting Agent → Hashing Agent:
{
  meeting_id: "mtg_123",
  times: [all 16 times]
}

Hashing Agent computes (deterministically):
hash_001 = SHA256("mtg_123||2026-01-16 09:00")
hash_002 = SHA256("mtg_123||2026-01-16 09:30")
hash_003 = SHA256("mtg_123||2026-01-16 10:00")
hash_004 = SHA256("mtg_123||2026-01-16 10:30")
...
hash_016 = SHA256("mtg_123||2026-01-16 16:30")

Hashing Agent → Meeting Agent:
{
  hashes: [hash_001, hash_002, hash_003, ..., hash_016]
  // NOTE: NO MAPPING SENT TO MEETING AGENT
}

Hashing Agent → Alice's Agent:
{
  meeting_id: "mtg_123",
  hash_to_time: {
    hash_001: "2026-01-16 09:00",
    hash_002: "2026-01-16 09:30",
    hash_003: "2026-01-16 10:00",
    hash_004: "2026-01-16 10:30",
    ...
    hash_016: "2026-01-16 16:30"
  }
}

Hashing Agent → Bob's Agent:
{
  meeting_id: "mtg_123",
  hash_to_time: {same mapping}
}

Hashing Agent → Carol's Agent:
{
  meeting_id: "mtg_123",
  hash_to_time: {same mapping}
}

Hashing Agent DELETES all state and returns to empty.

---

PHASE 2: UTILITY CALCULATION

Meeting Agent → All User Proxy Agents:
{
  meeting_id: "mtg_123",
  hashes: [hash_001, hash_002, hash_003, ...]
}

Alice's Agent checks her calendar:
- 09:00: Free, prefers morning → utility 85
- 09:30: Free, prefers morning → utility 90
- 10:00: Free, optimal time → utility 95
- 10:30: Customer call (existing, high priority) → utility 0
- 11:00: Free → utility 80
- ...
- 14:00: Free, post-lunch dip → utility 75

Alice's Agent creates hash→utility mapping using local hash_to_time:
{
  hash_001: 85,   // 09:00
  hash_002: 90,   // 09:30
  hash_003: 95,   // 10:00
  hash_004: 0,    // 10:30 (busy)
  hash_005: 80,   // 11:00
  ...
}

Alice's Agent → Meeting Agent:
{
  agent_id: "alice",
  utilities: {
    hash_001: 85,
    hash_002: 90,
    hash_003: 95,
    hash_005: 80,
    // Note: hash_004 (utility 0) NOT SENT
    ...
  }
}

Bob's Agent checks his calendar:
- 09:00: Free, not a morning person → utility 60
- 09:30: Free → utility 70
- 10:00: Free → utility 80
- 10:30: Free → utility 85
- 11:00: Free → utility 90
- ...

Bob's Agent → Meeting Agent:
{
  agent_id: "bob",
  utilities: {
    hash_001: 60,
    hash_002: 70,
    hash_003: 80,
    hash_004: 85,
    hash_005: 90,
    ...
  }
}

Carol's Agent checks her calendar:
- 09:00: Free, but not preferred → utility 40
- 09:30: Free → utility 50
- 10:00: Free → utility 60
- 10:30: Free, prefers late morning → utility 95
- ...

Carol's Agent → Meeting Agent:
{
  agent_id: "carol",
  utilities: {
    hash_001: 40,
    hash_002: 50,
    hash_003: 60,
    hash_004: 95,
    ...
  }
}

---

PHASE 3: AGGREGATION

Meeting Agent receives utilities from all agents and buckets by hash:

hash_001: 
  - Alice: 85 (weight 3.0 as host)
  - Bob: 60 (weight 1.5 as required)
  - Carol: 40 (weight 1.0 as optional)

hash_002:
  - Alice: 90 (weight 3.0)
  - Bob: 70 (weight 1.5)
  - Carol: 50 (weight 1.0)

hash_003:
  - Alice: 95 (weight 3.0)
  - Bob: 80 (weight 1.5)
  - Carol: 60 (weight 1.0)

hash_004:
  - Alice: 0 (NOT SENT - treated as 0)
  - Bob: 85 (weight 1.5)
  - Carol: 95 (weight 1.0)

Meeting Agent applies weights and calculates weighted sum:

hash_001: (85 × 3.0) + (60 × 1.5) + (40 × 1.0) = 255 + 90 + 40 = 385
hash_002: (90 × 3.0) + (70 × 1.5) + (50 × 1.0) = 270 + 105 + 50 = 425
hash_003: (95 × 3.0) + (80 × 1.5) + (60 × 1.0) = 285 + 120 + 60 = 465 ← WINNER
hash_004: (0 × 3.0) + (85 × 1.5) + (95 × 1.0) = 0 + 127.5 + 95 = 222.5

Meeting Agent identifies: hash_003 has highest weighted utility (465)

Meeting Agent does NOT know that hash_003 = "2026-01-16 10:00"!

---

PHASE 4: NOTIFY INITIATOR ONLY

Meeting Agent → Alice's Agent (initiator only):
{
  meeting_id: "mtg_123",
  status: "scheduling_complete",
  winning_hash: hash_003
}

Alice's Agent:
- Looks up hash_003 in local hash_to_time mapping
- Discovers: hash_003 → "2026-01-16 10:00"
- Updates Alice's local calendar: "Customer Call @ 2026-01-16 10:00"

Meeting Agent's job is COMPLETE.
Meeting Agent never learns the scheduled time.

---

PHASE 5: INITIATOR SENDS INVITES

Alice's Agent → Bob's Agent:
{
  meeting_id: "mtg_123",
  title: "Customer Call",
  organizer: "alice",
  scheduled_time: "2026-01-16 10:00",
  participants: ["alice", "bob", "carol"]
}

Alice's Agent → Carol's Agent:
{
  meeting_id: "mtg_123",
  title: "Customer Call",
  organizer: "alice",
  scheduled_time: "2026-01-16 10:00",
  participants: ["alice", "bob", "carol"]
}

Bob's Agent: 
- Updates Bob's calendar
- Sends confirmation to Alice's Agent: "Accepted"

Carol's Agent:
- Updates Carol's calendar
- Sends confirmation to Alice's Agent: "Accepted"

Alice's Agent → Alice (user notification):
{
  message: "Customer Call scheduled for Jan 16 at 10:00 AM",
  status: "All participants confirmed"
}

DONE!
```

### 2.3 Why This Architecture Solves the Problem

**Privacy (Constraint 1)**: 
- User Proxy Agents never send raw times to Meeting Agent
- Meeting Agent never sees which times are available, only hashes and utilities
- Meeting Agent never learns the final scheduled time
- Hashing Agent is stateless and cannot correlate data
- Only the initiator knows the final outcome (acceptable - they organized it)

**Gated Access (Constraint 2)**:
- Each User Proxy Agent manages its own calendar
- No central calendar database needed
- Agents communicate only through hashes during coordination
- Final invites sent peer-to-peer between User Agents

**Inference Prevention (Constraint 3)**:
- All hashes sent simultaneously (no sequential queries)
- Meeting Agent cannot ask "is this hash for 9 AM?" because it doesn't have the mapping
- Hashing Agent is stateless, cannot build profiles across meetings
- Even if Meeting Agent is malicious, it only sees hashes and utilities, never times
- No central service accumulates knowledge of scheduled times

**Intelligent Rescheduling (Constraint 4)**:
- User Proxy Agent calculates utilities based on meeting type, time preferences, and history
- Can assign low utility to meetings it will reschedule, high utility to meetings it won't
- Meeting Agent respects these utilities in aggregation
- Learning happens locally in each User Proxy Agent

**Hierarchical Priorities (Constraint 5)**:
- Meeting Agent applies importance weights during aggregation
- Initiator/host preferences weighted 3x more than optional attendees
- Required attendees weighted 1.5x
- Ensures organizer's schedule is prioritized

### 2.4 Security Properties

**What the Meeting Agent Cannot Learn**:
- Which times are available for which users ✗
- Which users are available at the same time ✗
- User preferences for specific times ✗
- User calendar structure ✗
- Patterns across multiple meetings ✗
- **The final scheduled time ✗** ← KEY IMPROVEMENT

**What the Hashing Agent Cannot Learn**:
- Which users are available ✗
- Which times are preferred ✗
- User identities ✗
- Patterns across users ✗
- Patterns across meetings ✗
- Which hash won ✗

**What User Proxy Agents Protect**:
- Raw calendar data (never sent) ✓
- Time preferences (only sent as utilities) ✓
- Meeting priorities (only sent as utilities) ✓

**What the Initiator Learns**:
- The final scheduled time ✓
- This is acceptable because:
  - They organized the meeting
  - They need to send invites
  - This matches real-world meeting organization
  - They already participated in utility submission

### 2.5 Attack Resistance

**Attack 1: Malicious Meeting Agent tries to reconstruct calendars**
- Cannot map hashes to times (doesn't have the mapping)
- Cannot correlate across meetings (each meeting_id produces different hashes)
- Cannot learn final scheduled time (only initiator receives winning hash)
- **Result: BLOCKED ✓**

**Attack 2: Meeting Agent tries to regenerate hashes**
- Knows the original times it sent to Hashing Agent
- Could try to compute: SHA256("mtg_123||09:00"), SHA256("mtg_123||09:30"), ...
- Would successfully regenerate all hashes
- **Result: PARTIAL SUCCESS but LIMITED IMPACT**
- Can map hashes to times for this specific meeting
- But still doesn't know which users are available when
- Cannot learn final scheduled time (doesn't receive winning hash unless it's the initiator)
- Cannot correlate across meetings (different meeting_ids)

**Note**: If absolute prevention of hash regeneration is required, use:
`hash = SHA256(meeting_id || time || shared_secret)`
where shared_secret is distributed to User Agents but not Meeting Agent.
This adds complexity - recommend for v2.

**Attack 3: Collusion between User Agents**
- Alice and Bob compare notes to infer Carol's availability
- Example: "In meeting X, what utility did you give hash_042?"
- If Alice gave 80 and Bob gave 70, and aggregate was 150, implies Carol gave 0
- **Result: POSSIBLE**
- This requires active collusion between participants
- Mitigation would require secure multi-party computation (much more complex)
- Accept this as a limitation for v1

**Attack 4: Hashing Agent stores state secretly**
- Could keep hash→time mapping in memory
- Could build profiles over time
- **Result: TRUST ASSUMPTION**
- We assume Hashing Agent is honest-but-curious
- Can be mitigated by:
  - Open source implementation
  - Third-party audits
  - Run your own Hashing Agent
  - Use trusted execution environments (TEE)

---

## Part 3: Implementation Overview

### 3.1 Technology Stack

**Backend**:
- Language: Python 3.11+
- Framework: FastAPI
- Cryptography: hashlib (built-in SHA256)
- Communication: WebSockets for real-time coordination
- Storage: Redis for temporary session state (Meeting Agent only)

**Frontend**:
- Framework: React 19
- UI Library: shadcn/ui
- State Management: Zustand
- Calendar Display: react-big-calendar

**Deployment**:
- Docker for containerization
- Each agent as separate container
- Docker Compose for local development

### 3.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Proxy Agent (Alice)                  │
│  - Local calendar storage                                    │
│  - Utility calculation engine                                │
│  - Hash→time mapping storage                                 │
│  - Peer-to-peer invite sender                                │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│                      Meeting Agent                           │
│  - Coordination logic                                        │
│  - Weighted aggregation                                      │
│  - Hash bucketing                                            │
│  - Session management (meeting_id tracking)                  │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│                      Hashing Agent                           │
│  - Stateless hash generation                                 │
│  - SHA256 computation                                        │
│  - No persistent storage                                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Implementation Phases

**Phase 1 (Week 1): Core Infrastructure**
- Set up three-agent communication framework
- Implement basic WebSocket connections
- Build hash generation and verification
- Create simple data models

**Deliverables**:
- Three agents can communicate
- Hashing Agent generates deterministic hashes
- Basic test suite

**Phase 2 (Week 2): Utility Calculation & Aggregation**
- Implement utility calculation in User Proxy Agent
- Build weighted aggregation in Meeting Agent
- Add importance level support
- Create hash bucketing logic

**Deliverables**:
- User Agents can calculate utilities based on mock calendar
- Meeting Agent can aggregate and find winner
- Unit tests for aggregation logic

**Phase 3 (Week 3): Privacy Features**
- Implement hash→time mapping distribution
- Ensure Meeting Agent never receives mapping
- Add initiator-only winner notification
- Build peer-to-peer invite system

**Deliverables**:
- Privacy guarantees verified
- Only initiator learns scheduled time
- Security test suite

**Phase 4 (Week 4): Calendar Integration & UI**
- Build meeting request form
- Create calendar view for User Agents
- Implement preferences dashboard
- Add meeting confirmation flow

**Deliverables**:
- Working UI for all three agents
- Demo-ready interface
- User can create and accept meetings

**Phase 5 (Week 5): Intelligence & Learning**
- Add time preference learning
- Implement meeting priority detection
- Build utility score optimization
- Track historical patterns

**Deliverables**:
- Agents learn user preferences over time
- Utility scores improve with usage
- Preference visualization in UI

**Phase 6 (Week 6): Testing, Documentation & Demo**
- End-to-end integration tests
- Security audit
- Write documentation
- Create demo video
- Prepare presentation

**Deliverables**:
- Comprehensive test coverage
- Security analysis document
- Demo video showing privacy preservation
- README with architecture explanation

---

## Part 4: Code Structure

### 4.1 Directory Structure

```
privacy-meeting-scheduler/
├── agents/
│   ├── user_proxy/
│   │   ├── __init__.py
│   │   ├── agent.py              # UserProxyAgent class
│   │   ├── calendar.py           # Calendar management
│   │   ├── utility.py            # Utility calculation
│   │   └── invite_sender.py      # Peer-to-peer invites
│   ├── meeting/
│   │   ├── __init__.py
│   │   ├── agent.py              # MeetingAgent class
│   │   ├── aggregation.py        # Weighted aggregation
│   │   └── coordination.py       # Meeting coordination logic
│   └── hashing/
│       ├── __init__.py
│       └── agent.py              # HashingAgent (stateless)
├── common/
│   ├── __init__.py
│   ├── models.py                 # Shared data models
│   ├── communication.py          # WebSocket helpers
│   └── crypto.py                 # Hashing utilities
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MeetingForm.tsx
│   │   │   ├── CalendarView.tsx
│   │   │   └── PreferencesPanel.tsx
│   │   ├── stores/
│   │   │   └── meetingStore.ts
│   │   └── App.tsx
│   └── package.json
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
├── docker-compose.yml
├── Dockerfile.user_proxy
├── Dockerfile.meeting
├── Dockerfile.hashing
└── README.md
```

### 4.2 Key Interfaces

```python
# common/models.py

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class MeetingRequest:
    meeting_id: str
    initiator: str
    title: str
    participants: List[Participant]
    scheduling_window: SchedulingWindow

@dataclass
class Participant:
    id: str
    role: str  # "host", "attendee"
    importance: str  # "mandatory", "required", "optional"

@dataclass
class HashMapping:
    meeting_id: str
    hash_to_time: Dict[str, str]

@dataclass
class UtilitySubmission:
    agent_id: str
    utilities: Dict[str, int]  # hash → utility score

@dataclass
class WinnerNotification:
    meeting_id: str
    winning_hash: str

@dataclass
class MeetingInvite:
    meeting_id: str
    title: str
    organizer: str
    scheduled_time: str
    participants: List[str]
```

---

## Part 5: Demo Narrative

### 5.1 Demo Script

**Setup**: Three browser windows showing Alice's Agent, Bob's Agent, and Meeting Agent dashboard.

**Step 1: Alice Creates Meeting**
```
Alice's Agent UI:
[Create New Meeting Button]
- Title: "Q1 Planning Session"
- Participants: Bob (required), Carol (optional)
- Window: Jan 16, 9 AM - 5 PM
[Send Request]

Narrator: "Alice wants to schedule a planning session with Bob and Carol. 
Notice that Alice's Agent has access to her calendar, but the Meeting Agent 
and other participants do not."
```

**Step 2: Show Hashing Process**
```
Meeting Agent Dashboard:
"Generating 16 time slot hashes for meeting mtg_456..."
[Show hash_001, hash_002, hash_003... without times]

Narrator: "The Meeting Agent generates 16 possible time slots and sends 
them to the Hashing Agent. Critically, the Meeting Agent receives back 
only HASHES - it cannot map these to actual times."
```

**Step 3: Show Utility Calculation**
```
Alice's Agent UI:
"Calculating utilities for meeting mtg_456..."
[Show calendar with color-coded preferences]
- 9:00 AM: Green (available, utility 85)
- 10:00 AM: Green (available, utility 95)
- 10:30 AM: Red (busy - customer call)
- 2:00 PM: Yellow (available, utility 75)

Narrator: "Alice's Agent calculates utility scores based on her calendar. 
Notice 10:30 AM is blocked by an existing customer call. The Agent maps 
these utilities to hashes and sends ONLY the hash-utility pairs to the 
Meeting Agent - never the actual times."
```

**Step 4: Show Bob's Different Preferences**
```
Bob's Agent UI:
"Calculating utilities for meeting mtg_456..."
- 9:00 AM: Yellow (not a morning person, utility 60)
- 10:00 AM: Green (utility 80)
- 10:30 AM: Green (utility 85)
- 2:00 PM: Green (utility 90)

Narrator: "Bob has different preferences - he's not a morning person. 
His Agent also sends hash-utility pairs to the Meeting Agent."
```

**Step 5: Show Aggregation**
```
Meeting Agent Dashboard:
"Aggregating utilities with weights..."
"Alice (host): 3.0x weight"
"Bob (required): 1.5x weight"
"Carol (optional): 1.0x weight"

[Show bar chart of weighted utilities per hash]
hash_003: 465 ← WINNER
hash_004: 222
hash_005: 380

Narrator: "The Meeting Agent aggregates utilities using importance weights. 
Alice, as the host, has 3x weight. hash_003 wins with a score of 465. 
But here's the key: the Meeting Agent has NO IDEA what time hash_003 
represents!"
```

**Step 6: Show Winner Notification (Initiator Only)**
```
Alice's Agent UI:
"Meeting scheduled! Winning hash: hash_003"
[Agent looks up hash_003 in local mapping]
"hash_003 = 10:00 AM"
[Calendar updates: "Q1 Planning Session @ 10:00 AM"]

Meeting Agent Dashboard:
[Shows: "Meeting mtg_456: Scheduled (hash_003)"]
[Does NOT show the time]

Narrator: "The Meeting Agent sends the winning hash ONLY to Alice, 
the initiator. Alice's Agent looks it up in its local mapping and 
discovers the meeting is at 10:00 AM. Notice the Meeting Agent never 
learns this - its job is done."
```

**Step 7: Show Peer-to-Peer Invites**
```
Alice's Agent → Bob's Agent:
[Send calendar invite]
"Q1 Planning Session"
"Jan 16, 10:00 AM"
"Organizer: Alice"

Bob's Agent UI:
[Notification pops up]
[Calendar updates with new meeting]
"Accepted ✓"

Narrator: "Alice's Agent sends calendar invites directly to Bob and Carol. 
This is peer-to-peer communication - the Meeting Agent is not involved. 
The entire meeting coordination happened with the Meeting Agent never 
seeing anyone's calendar or even learning the final scheduled time."
```

**Step 8: Security Visualization**
```
[Split screen showing what each agent knows]

Meeting Agent:
✓ Knows: hash_003 won
✓ Knows: Aggregate utilities per hash
✗ Doesn't know: What time hash_003 is
✗ Doesn't know: Anyone's calendar
✗ Doesn't know: Final scheduled time

Alice's Agent:
✓ Knows: Own calendar
✓ Knows: Final time (10:00 AM)
✗ Doesn't know: Bob's calendar
✗ Doesn't know: Carol's calendar

Bob's Agent:
✓ Knows: Own calendar
✓ Knows: Final time (received invite)
✗ Doesn't know: Alice's calendar
✗ Doesn't know: Carol's calendar

Narrator: "This is privacy-preserving coordination. Each agent only knows 
what it absolutely needs to know. Even if the Meeting Agent were compromised, 
it couldn't reconstruct anyone's calendar because it never sees the hash-time 
mapping or the final scheduled time."
```

---

## Part 6: Future Enhancements

### 6.1 Enhanced Privacy (v2)

**Salted Hashing**: Prevent Meeting Agent from regenerating hashes
```
hash = SHA256(meeting_id || time || shared_secret)
```
Shared secret distributed to User Agents but not Meeting Agent.

**Differential Privacy