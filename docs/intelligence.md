# Intelligence & Learning

## The Big Idea

**User Proxy Agent = Calendar + LLM → Utility Score.** That's the whole intelligence layer.

The LLM runs privately on each user's side, seeing their full calendar context. It outputs a simple utility score (0-100) for each time slot. Meeting Agent aggregates these scores without ever seeing the reasoning.

---

## Where Intelligence Lives

```
┌─────────────────────────────────────────────────────────────┐
│                    User Proxy Agent                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              LLM-Powered Intelligence                │    │
│  │  - Parses meeting metadata (title, attendees, desc) │    │
│  │  - Considers calendar conflicts                      │    │
│  │  - Applies learned preferences                       │    │
│  │  - Decides when to escalate vs act autonomously      │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│                    Utility Score (0-100)                     │
│                           ↓                                  │
│              hash→utility pairs (sent to Meeting Agent)      │
└─────────────────────────────────────────────────────────────┘
```

**Why this preserves privacy:**
- LLM runs locally (or on user's trusted service)
- Calendar context never leaves the User Proxy Agent
- Meeting Agent only sees hashes + utility scores
- Intelligence is distributed, not centralized

---

## The Single Prompt

One LLM call does everything:

```
You are a scheduling assistant for {user_name}.

MEETING REQUEST:
- Title: {title}
- Organizer: {organizer}
- Type: {meeting_type}
- Duration: {duration}

CALENDAR STATE FOR EACH TIME SLOT:
- Slot A (hash_001): Free
- Slot B (hash_002): "1:1 with Sarah" (internal, recurring, importance 5)
- Slot C (hash_003): "Customer call with Acme" (external, importance 9)
- Slot D (hash_004): Free

USER PREFERENCES (learned from past decisions):
- Rescheduled "Team standup" for "Customer demo" ✓
- Declined to reschedule "Manager 1:1" for "Vendor call" ✗
- Prefers morning meetings

For each slot, output a utility score 0-100:
- 100 = perfect (free, preferred time)
- 70-99 = good (free, acceptable)
- 40-69 = willing to reschedule conflict
- 1-39 = reluctant
- 0 = absolutely not

Output JSON with reasoning.
```

**One prompt. One response. Done.**

---

## Utility Scoring Logic

### Base Score by Availability

| Slot State | Base Score | Reasoning |
|------------|------------|-----------|
| Free | 80-100 | Adjusted by time-of-day preference |
| Low-importance conflict (1-4) | 50-70 | Willing to reschedule |
| Medium-importance conflict (5-7) | 20-40 | Reluctant |
| High-importance conflict (8-10) | 0-10 | Protected |
| External meeting | 0 | Never reschedule |

### Modifiers

**Time of Day** (user-specific):
- Morning person: 9-11 AM gets +10
- Lunch hour: 12-1 PM gets -10
- Post-lunch dip: 1-2 PM gets -5

**Meeting Type Match**:
- Incoming external + existing internal: +20 to reschedule willingness
- Incoming 1:1 + existing team meeting: neutral
- Incoming team + existing customer call: -50 (protect customer)

**Learned Preferences** (from history):
- "User always protects manager 1:1s": manager_1on1 → score 0
- "User reschedules standups for customers": team_standup + customer → score 60

---

## Learning System

### What We Store

```python
class SchedulingDecision:
    user_id: str
    timestamp: datetime
    meeting_type: str           # What was being scheduled
    conflicting_type: str       # What would have been rescheduled
    recommended_action: str     # What the system suggested
    user_action: str            # "accepted", "rejected", "modified"
```

### How Learning Works

1. **Record**: Every scheduling decision is logged
2. **Extract**: Convert to few-shot examples
3. **Inject**: Add to prompt for future requests

```
PAST DECISIONS:
- Rescheduled "Team standup" for "Customer demo" (approved)
- Declined to reschedule "Manager 1:1" for "Vendor call" (rejected)
- Rescheduled "All-hands prep" for "Board meeting" (approved)
```

**No fine-tuning. No embeddings. No ML pipeline.** Just prompt engineering with historical examples.

### Why This Works

- LLM generalizes from examples ("Manager meetings are protected")
- New scenarios handled by reasoning ("CTO 1:1 is like Manager 1:1")
- User corrections improve future accuracy
- Transparent—user can see what was learned

---

## Escalation Logic

```python
def should_escalate(utilities: dict) -> tuple[bool, str]:
    scores = list(utilities.values())
    
    # No good options
    if max(scores) < 50:
        return True, "No slots scored above 50"
    
    # Too close to call
    top_two = sorted(scores, reverse=True)[:2]
    if len(top_two) >= 2 and top_two[0] - top_two[1] < 10:
        return True, "Top options too close to call"
    
    # High-stakes meeting (could add)
    # if incoming_meeting.importance > 8:
    #     return True, "High-stakes meeting needs confirmation"
    
    return False, None
```

### When Escalating

Show the user:
1. Top 2-3 options with times
2. Score breakdown for each
3. What would be rescheduled (if anything)
4. LLM's reasoning

User picks → decision recorded → learning improves.

---

## Mock vs Real LLM

### Mock Mode (Default)

Deterministic logic for testing:
```python
if slot.is_free:
    score = 80 + morning_bonus - lunch_penalty
elif slot.conflict.external:
    score = 0
elif slot.conflict.importance < 5:
    score = 60
else:
    score = 10
```

**Pros**: Fast, predictable, no API costs  
**Cons**: No real reasoning, limited flexibility

### OpenAI Mode

Real GPT-4 for production:
```python
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)
utilities = json.loads(response.choices[0].message.content)
```

**Pros**: Real reasoning, handles edge cases, learns from examples  
**Cons**: Latency, cost, requires API key

### Switching Modes

```bash
# In .env
LLM_MODE=mock    # For development
LLM_MODE=openai  # For production
```

---

## What We Explicitly DON'T Do

| Over-engineered | Our approach |
|-----------------|--------------|
| Separate classification model | One prompt sees meeting metadata |
| Rescheduling decision tree | LLM outputs score reflecting willingness |
| Embedding-based preference matching | Few-shot examples in prompt |
| Complex multi-turn negotiation | Single utility response per user |
| Centralized preference model | Each user's agent learns independently |

---

## Future Enhancements (v2+)

### Smarter Learning
- Cluster similar decisions ("protects all 1:1s, not just manager")
- Confidence scoring on learned preferences
- User can review/edit learned preferences

### Richer Context
- Org chart integration (who reports to whom)
- Meeting history (how often do they meet?)
- Email context (is this urgent?)

### Multi-Turn Negotiation
- "Alice can't make 2pm, would 3pm work?"
- Coordinator proposes alternatives
- Users respond with updated utilities

---

## See Also

- [Architecture](architecture.md) - How agents communicate
- [Security](security.md) - Why this is private
