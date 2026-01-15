# The Elegant Solution

## One Sentence

**User Proxy Agent = Calendar + LLM → Utility Score.** That's the whole intelligence layer.

---

## The Minimal Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   User Proxy Agent                        │
│                                                           │
│   Calendar ──→ LLM ──→ utility score per hash             │
│                                                           │
│   "Given my calendar and this meeting request,            │
│    how much do I want each time slot? 0-100"              │
└──────────────────────────────────────────────────────────┘
                          │
                          │ {hash_001: 85, hash_002: 0, ...}
                          ▼
                  ┌───────────────┐
                  │ Meeting Agent │  (aggregates, picks winner)
                  └───────────────┘
                          │
                          │ winning_hash
                          ▼
                     Initiator decrypts, sends invites
```

**That's it.** Security comes from hashes. Intelligence comes from one LLM call.

---

## The Single Prompt

When Meeting Agent asks for utilities, User Proxy Agent runs ONE prompt:

```
You are a scheduling assistant for {user_name}.

MEETING REQUEST:
- Title: {incoming_title}
- Organizer: {organizer}
- Attendees: {attendee_list}
- Type: {meeting_type}
- Duration: {duration}

CALENDAR STATE FOR EACH TIME SLOT:
- Slot A (hash_001): Free
- Slot B (hash_002): "1:1 with Sarah" (internal, recurring)
- Slot C (hash_003): "Customer call with Acme" (external)
- Slot D (hash_004): Free
- ...

USER PREFERENCES (learned):
- Prefers mornings
- Protects customer calls
- Will reschedule internal 1:1s for external meetings

For each slot, output a utility score 0-100.
Higher = user wants this slot more.
0 = absolutely not (hard conflict).

Output JSON:
{
  "hash_001": <score>,
  "hash_002": <score>,
  ...
}
```

**One prompt. One response. Done.**

---

## Why This Works

### Security (unchanged)
- Meeting Agent sees hashes, not times
- Meeting Agent sees utilities, not calendar
- Hashing Agent is stateless
- Initiator-only decryption

### Intelligence (now simple)
- LLM sees full context in one shot
- No separate classification/rescheduling/escalation phases
- LLM naturally handles trade-offs ("reschedule 1:1 for customer? → give that slot a 70")
- Preferences injected via prompt, not complex learning pipeline

### Learning (minimal)
- Store user overrides: "User chose slot B when I recommended A"
- Append to prompt as few-shot examples
- No fine-tuning, no embeddings, no ML pipeline

```
PAST DECISIONS:
- Rescheduled "Team standup" for "Customer demo" (approved)
- Declined to reschedule "Manager 1:1" for "Vendor call" (rejected)
```

---

## Escalation (simple rule)

```python
def should_escalate(utilities: dict) -> bool:
    scores = list(utilities.values())
    
    # No good options
    if max(scores) < 50:
        return True
    
    # Too close to call
    top_two = sorted(scores, reverse=True)[:2]
    if top_two[0] - top_two[1] < 10:
        return True
    
    return False
```

If escalate: show user the top 2-3 options with LLM's reasoning.
If not: proceed automatically.

---

## What We Cut

| Over-engineered | Elegant replacement |
|-----------------|---------------------|
| Separate classification LLM | One prompt sees meeting metadata |
| Separate rescheduling logic | LLM outputs score reflecting willingness to reschedule |
| Learning pipeline with embeddings | Few-shot examples in prompt |
| Complex scoring formula | LLM outputs the score directly |
| Multiple escalation conditions | Two simple rules (low max, close call) |

---

## Implementation: 3 Files

### 1. user_proxy_agent.py
```python
async def calculate_utilities(
    meeting_request: MeetingRequest,
    hash_to_time: dict[str, datetime],
    calendar: Calendar,
    preferences: UserPreferences
) -> dict[str, int]:
    
    # Build calendar state for each slot
    slot_states = {}
    for hash_id, time in hash_to_time.items():
        conflict = calendar.get_event_at(time)
        slot_states[hash_id] = describe_slot(time, conflict)
    
    # One LLM call
    prompt = build_utility_prompt(
        meeting_request,
        slot_states,
        preferences.to_few_shot_examples()
    )
    
    response = await llm.complete(prompt)
    utilities = parse_utility_response(response)
    
    # Check escalation
    if should_escalate(utilities):
        utilities = await escalate_to_user(utilities, meeting_request)
    
    return utilities
```

### 2. meeting_agent.py
```python
async def coordinate_meeting(request: MeetingRequest) -> str:
    # Generate times, get hashes
    times = generate_time_slots(request.window)
    hashes = await hashing_agent.hash_times(request.meeting_id, times)
    
    # Collect utilities from all participants
    all_utilities = await gather([
        user_agent.calculate_utilities(request, hashes)
        for user_agent in request.participants
    ])
    
    # Aggregate with weights
    winner = aggregate_utilities(all_utilities, request.weights)
    
    # Return winning hash to initiator only
    return winner
```

### 3. hashing_agent.py
```python
def hash_times(meeting_id: str, times: list[datetime]) -> HashResult:
    mapping = {
        sha256(f"{meeting_id}||{t}").hexdigest(): t
        for t in times
    }
    
    # Send only hashes to Meeting Agent
    # Send full mapping to User Agents
    return HashResult(
        hashes=list(mapping.keys()),
        mapping=mapping  # distributed to User Agents only
    )
```

---

## The Whole System in One Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SCHEDULING FLOW                          │
│                                                                  │
│  1. Alice wants to meet Bob & Carol                              │
│                                                                  │
│  2. Meeting Agent: "Here are hashes for 16 time slots"           │
│                                                                  │
│  3. Each User Agent (in parallel):                               │
│     - Receives hash→time mapping                                 │
│     - Feeds calendar + meeting info to LLM                       │
│     - LLM outputs: {hash: utility} for all slots                 │
│     - Returns utilities to Meeting Agent                         │
│                                                                  │
│  4. Meeting Agent:                                               │
│     - Aggregates utilities by hash                               │
│     - Applies weights (host 3x, required 1.5x, optional 1x)      │
│     - Picks winning hash                                         │
│     - Sends ONLY to Alice (initiator)                            │
│                                                                  │
│  5. Alice's Agent:                                               │
│     - Decrypts hash → "Jan 16, 10 AM"                            │
│     - Sends calendar invites to Bob & Carol                      │
│                                                                  │
│  DONE. Meeting Agent never learned the time.                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why This Is Elegant

1. **Single responsibility**: Each agent does one thing
2. **Single LLM call**: All intelligence in one prompt
3. **No state**: Hashing Agent stateless, Meeting Agent forgets after coordination
4. **Privacy by design**: Architecture makes leaks impossible, not just difficult
5. **Learning without ML**: Few-shot examples in prompt, no training pipeline
6. **Escalation without rules engine**: Two simple numeric checks

**Total complexity: ~300 lines of Python.**
