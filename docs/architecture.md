# Architecture: Privacy-Preserving Multi-Agent Scheduling

## The Core Insight

Traditional schedulers see everything. Meeting Safe sees nothing but hashes — yet still finds the perfect time.

The key innovation is **initiator-only decryption**: the coordination agent never learns the scheduled time. Only the meeting organizer can decode the winning hash.

---

## Three-Agent Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User Agent A   │     │  User Agent B   │     │  User Agent C   │
│  (has calendar) │     │  (has calendar) │     │  (has calendar) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ hash→utility          │ hash→utility          │ hash→utility
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │     Meeting Agent      │
                    │  (sees hashes only,    │
                    │   never times)         │
                    └────────────┬───────────┘
                                 │
                                 │ winning hash
                                 ▼
                         ┌───────────────┐
                         │   Initiator   │
                         │  (decrypts,   │
                         │ sends invites)│
                         └───────────────┘
```

### Agent 1: User Proxy Agent

**Runs**: Locally on user's machine (or user's trusted service)

**Responsibility**: Knows the user's calendar and preferences

**Process**:
1. Receives hash→time mapping from Hashing Agent
2. Calculates utility score for each time based on calendar (0-100)
3. Uses LLM to consider preferences, conflicts, and tradeoffs
4. Sends only hash/utility pairs to Meeting Agent (never raw times)
5. If initiator: receives winning hash, decrypts to time, sends invites

**Privacy**: Calendar never leaves the user's agent

### Agent 2: Meeting Agent

**Runs**: Central coordination service

**Responsibility**: Coordinates scheduling across all participants

**Process**:
1. Generates all possible times in scheduling window
2. Gets hashes from Hashing Agent (NOT the mapping)
3. Distributes hashes to all User Proxy Agents
4. Collects hash/utility pairs from all agents
5. Aggregates with importance weights
6. Sends winning hash ONLY to initiating agent

**Privacy**: Never sees raw calendar data, never sees hash→time mapping, never learns scheduled time

### Agent 3: Hashing Agent

**Runs**: Stateless cryptographic service

**Responsibility**: Provides privacy through deterministic hashing

**Process**:
1. For each time: `hash = SHA256(meeting_id || time)`
2. Sends list of hashes to Meeting Agent (no mapping)
3. Sends full hash→time mapping to each User Proxy Agent
4. Immediately deletes all state

**Privacy**: Stateless; cannot correlate across users or meetings

---

## Data Flow Example

### Phase 1: Meeting Request

Alice wants to schedule with Bob and Carol.

```
Alice → Meeting Agent:
{
  meeting_id: "mtg_123",
  participants: ["alice", "bob", "carol"],
  window: "Tomorrow 9am-5pm"
}
```

### Phase 2: Hash Generation

```
Meeting Agent → Hashing Agent:
  "Generate hashes for 9am, 9:30am, 10am..."

Hashing Agent → Meeting Agent:
  [hash_001, hash_002, hash_003, ...]  // NO mapping!

Hashing Agent → Each User Agent:
  {hash_001: "9:00am", hash_002: "9:30am", ...}  // Full mapping
```

### Phase 3: Private Utility Calculation

Each User Proxy Agent:
1. Looks up their calendar
2. Calculates utility per slot
3. Sends back hash→utility (never revealing times)

```
Alice's Agent → Meeting Agent:
  {hash_001: 85, hash_002: 90, hash_003: 0, ...}

Bob's Agent → Meeting Agent:
  {hash_001: 60, hash_002: 70, hash_003: 80, ...}
```

**Meeting Agent sees**: hash_003 has low score from Alice  
**Meeting Agent does NOT know**: hash_003 = 10:00am = customer call conflict

### Phase 4: Aggregation

Meeting Agent aggregates (with weights):
- hash_001: (85×3) + (60×1.5) + (40×1) = 385
- hash_002: (90×3) + (70×1.5) + (50×1) = 425 ← Winner!

### Phase 5: Initiator-Only Decryption

```
Meeting Agent → Alice's Agent:
  {winning_hash: "hash_002"}

Alice's Agent:
  Looks up hash_002 → "9:30am"
  Creates calendar invite, sends to Bob & Carol
```

**Meeting Agent never learns that 9:30am was scheduled!**

---

## What Each Party Knows

| Party | Knows | Doesn't Know |
|-------|-------|--------------|
| Meeting Agent | Winning hash, aggregate utilities | Actual times, who's busy when, final scheduled time |
| User Agents | Own calendar, final time (via invite) | Other calendars, other utilities |
| Hashing Agent | Nothing (stateless) | Everything |

---

## Why This Design?

### Blocks Inference Attacks

A naive system:
```
Agent: "Free at 9?"     → "No"
Agent: "Free at 9:30?"  → "No"  
Agent: "Free at 10?"    → "Yes"
...calendar leaked through iteration
```

Our system: All slots submitted simultaneously. No iteration possible.

### Prevents Correlation

Different hashes per meeting_id:
- Meeting 123: hash("123||9:00am") = abc...
- Meeting 456: hash("456||9:00am") = xyz...

Coordinator can't correlate across meetings.

### Minimal Trust Requirements

- Hashing Agent: "honest-but-curious" (processes correctly, might try to learn)
- Meeting Agent: Same assumption
- User Agents: Trusted by their user only

Even if Meeting Agent is compromised, it only knows hashes and aggregate scores—not times, not individual availability.

---

## Implementation Files

```
prototype/agents/
├── user_proxy_agent.py   # Calendar access + LLM utility calculation
├── meeting_agent.py      # Coordination logic
└── hashing_agent.py      # SHA256 hashing
```

See [Security Model](security.md) for threat analysis.
