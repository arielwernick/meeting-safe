# Intelligence Brainstorm

## Where Intelligence Lives

In our three-agent architecture, **intelligence belongs in the User Proxy Agent**:

```
┌─────────────────────────────────────────────────────────────┐
│                    User Proxy Agent                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              LLM-Powered Intelligence                │    │
│  │  - Parses meeting metadata (title, attendees, desc) │    │
│  │  - Learns from historical behavior                   │    │
│  │  - Calculates context-aware utilities                │    │
│  │  - Decides when to escalate vs act autonomously      │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│                    Utility Calculator                        │
│                           ↓                                  │
│              hash→utility pairs (sent to Meeting Agent)      │
└─────────────────────────────────────────────────────────────┘
```

**Why this preserves privacy:**
- LLM runs locally (or with user's data only)
- Calendar never leaves the User Proxy Agent
- Meeting Agent only sees hashes + utility scores
- Intelligence is distributed, not centralized

---

## Meeting Attributes

**User-assigned (explicit):**
- Importance (0-10)
- Role: presenter / contributor / attendee / optional
- Meeting type: customer / internal / 1:1 / team / all-hands

**LLM-derived (implicit):**
- Has agenda (parse meeting body)
- External vs internal (check attendee domains)
- Recurring vs one-time (calendar metadata)
- Meeting category (infer from title + description)
- Relationship to organizer (org chart + history)
- Estimated value (based on attendees, title, context)

---

## LLM Integration Points

### 1. Meeting Classification (on calendar sync)

When a new meeting appears, LLM classifies it:

```python
def classify_meeting(meeting: Meeting) -> MeetingMetadata:
    """
    LLM prompt: Given this meeting, classify it.
    
    Input:
    - Title: "Weekly sync with Acme Corp"
    - Attendees: ["alice@mycompany.com", "bob@acmecorp.com"]
    - Description: "Review Q1 deliverables..."
    - Duration: 30 min
    - Recurring: weekly
    
    Output:
    {
      "category": "customer_sync",
      "external": true,
      "estimated_importance": 8,
      "moveable": false,
      "reason": "External customer meeting, recurring cadence"
    }
    """
```

### 2. Utility Calculation (on scheduling request)

When Meeting Agent requests utilities, LLM scores each slot:

```python
def calculate_utility(time_slot: datetime, meeting_request: MeetingRequest) -> int:
    """
    LLM considers:
    - What's already at this slot? (conflict analysis)
    - What's the relative importance? (new meeting vs existing)
    - User's historical preferences (time of day, meeting density)
    - Cascading effects (would rescheduling trigger chain reaction?)
    
    Returns: 0-100 utility score
    """
```

### 3. Rescheduling Decisions (conflict resolution)

When new meeting conflicts with existing:

```python
def should_reschedule(existing: Meeting, incoming: MeetingRequest) -> Decision:
    """
    LLM prompt: Should we reschedule the existing meeting?
    
    Existing: "1:1 with teammate" (internal, recurring, importance 5)
    Incoming: "Customer demo" (external, one-time, importance 9)
    
    Decision:
    {
      "action": "reschedule_existing",
      "confidence": 0.85,
      "reason": "Customer meetings take priority over internal 1:1s",
      "escalate": false  # confidence > threshold
    }
    """
```

### 4. Escalation Logic (uncertainty handling)

```python
def should_escalate(decision: Decision, context: Context) -> bool:
    """
    Escalate to user when:
    - Confidence < 0.7
    - High-stakes meeting (importance > 8)
    - User has overridden similar decisions before
    - Cascading effects detected
    - First time seeing this pattern
    """
```

---

## Scoring Model

### Base Score Formula

```
utility = base_availability × importance_modifier × preference_modifier × freshness_modifier
```

### Component Breakdown

**Base Availability (0 or 100):**
- Slot is free → 100
- Slot has conflict → 0 (unless reschedulable)

**Importance Modifier (0.0 - 2.0):**
- Based on meeting classification
- Customer call = 1.5x
- Manager 1:1 = 1.3x
- Team standup = 1.0x
- Optional sync = 0.7x

**Preference Modifier (0.5 - 1.5):**
- Learned from historical behavior
- User prefers mornings → morning slots get 1.3x
- User avoids post-lunch → 1-2 PM gets 0.7x
- User clusters meetings → adjacent to existing meeting gets 1.2x

**Freshness Modifier (0.8 - 1.2):**
- Newly scheduled = more moveable (0.8x protection)
- On calendar 2+ weeks = locked in (1.2x protection)

### Conflict Resolution Score

When slot has existing meeting, calculate reschedulability:

```
reschedule_score = 
    (incoming_importance - existing_importance) × 
    existing_moveability × 
    (1 - cascade_risk)
```

If `reschedule_score > threshold`:
- Utility = reschedule_score (willing to move existing)
- Else utility = 0 (protect existing meeting)

---

## Open Questions

**Contributor density:**
- Prefer times where more contributors already confirmed?
- How to handle chicken-and-egg (no one confirmed yet)?
- Does quorum matter?
- **Approach:** Meeting Agent could share "confirmation count" per hash (not who, just count)

**Role impact:**
- 1 of 2 contributors = hard to move (50% of value)
- 1 of 10 contributors = easier to move (10% of value)
- **Approach:** LLM infers role from attendee list + meeting type

**Relationship to organizer:**
- Manager 1:1 vs peer 1:1 vs team standup?
- **Approach:** LLM uses org chart data (if available) or learns from history

**Historical behavior:**
- Already skipped this meeting 3x?
- Always decline this organizer?
- **Approach:** User Proxy Agent maintains local history DB, LLM queries it

**Meeting freshness:**
- Scheduled yesterday = more moveable?
- On calendar 2 weeks = locked in?
- **Approach:** Freshness modifier in scoring formula

**External vs internal:**
- Customer call = never auto-reschedule?
- Internal sync = flexible?
- **Approach:** Hard rules + LLM classification

**Cascading effects:**
- Moving this meeting creates chain reaction?
- **Approach:** LLM simulates "what if I move this?" before scoring

---

## Learning Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    Learning Pipeline                         │
│                                                              │
│  1. OBSERVE: User accepts/declines/reschedules meetings      │
│  2. RECORD: Store decision + context in local history        │
│  3. LEARN: Fine-tune preference model on accumulated data    │
│  4. APPLY: Use updated model for future utility calculations │
│  5. VALIDATE: Track prediction accuracy, adjust confidence   │
└─────────────────────────────────────────────────────────────┘
```

**What we learn:**
- Time-of-day preferences (morning person? afternoon?)
- Meeting type preferences (loves 1:1s? hates all-hands?)
- Organizer preferences (always accepts from X? ignores Y?)
- Density preferences (clusters meetings? spreads them out?)
- Rescheduling patterns (which meetings get bumped?)

**How we learn:**
- Option A: Embedding-based similarity (find similar past decisions)
- Option B: Fine-tuned local LLM (train on user's history)
- Option C: Prompt engineering with few-shot examples from history

---

## Escalation

### When agent asks user vs decides autonomously

**Decide autonomously (confidence > 0.8):**
- Clear priority difference (customer vs internal sync)
- Matches historical pattern (user always accepts these)
- Low stakes (easily reversible)
- No cascading effects

**Escalate to user (confidence < 0.8):**
- First time seeing this pattern
- High-stakes meeting (C-level, customer, external)
- User has overridden similar decisions before
- Would require rescheduling 2+ existing meetings
- Ambiguous priority (two important meetings conflict)

### Escalation UX

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Your agent needs your input                             │
│                                                              │
│  New meeting request:                                        │
│  "Customer Demo with Acme" (Jan 16, 10:00 AM)               │
│                                                              │
│  Conflicts with:                                             │
│  "Weekly 1:1 with Sarah" (recurring, internal)              │
│                                                              │
│  Recommendation: Reschedule 1:1 to make room                │
│  Confidence: 72%                                             │
│                                                              │
│  [ Accept recommendation ]  [ Keep 1:1 ]  [ Decide later ]  │
│                                                              │
│  ☐ Remember this preference for similar situations          │
└─────────────────────────────────────────────────────────────┘
```

---

## Privacy-Preserving Intelligence

**Key insight:** All intelligence runs locally in User Proxy Agent

| Component | Runs Where | Sees What |
|-----------|-----------|-----------|
| Meeting classification LLM | User Proxy Agent | User's calendar only |
| Utility calculation | User Proxy Agent | User's calendar only |
| Preference learning | User Proxy Agent | User's history only |
| Escalation logic | User Proxy Agent | User's context only |
| Meeting Agent | Central service | Hashes + utilities only |

**LLM deployment options:**
1. **Local LLM** (Llama, Mistral): Full privacy, runs on user's device
2. **Cloud LLM with user's API key**: User controls their own data
3. **Encrypted inference**: Emerging tech, not production-ready

---

## Implementation Phases

### Phase 1: Rule-based scoring
- Hard-coded importance weights
- Simple time-of-day preferences
- External > internal rule

### Phase 2: LLM classification
- Auto-categorize meetings
- Infer importance from metadata
- Basic conflict resolution

### Phase 3: Learned preferences
- Track user decisions
- Build preference embeddings
- Personalized scoring

### Phase 4: Proactive scheduling
- Suggest meeting times before asked
- Predict scheduling conflicts
- Auto-reschedule low-priority meetings
