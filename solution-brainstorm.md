# Problem Statement

Meeting scheduling is easy when one agent has access to all calendars. It gets hard when access is gated—each agent only sees one person's calendar, yet meetings need to be scheduled across multiple people.

Beyond just finding open slots, the system should learn preferences over time. People have patterns: they skip certain meetings, they'll reschedule internal 1:1s to make room for customer calls, and they may want the agent to escalate when there's a conflict it can't resolve.

## 1. Coordination

## 2. Intelligence

## 3. Security

**Core threat:** Agents are chatty. An LLM-based coordinator will iteratively probe until it reconstructs everyone's calendar.

```
Agent: "Are you free at 9?"     → "No"
Agent: "Are you free at 9:30?"  → "No"  
Agent: "Are you free at 10?"    → "Yes"
...full calendar leaked through iteration
```

**Solution:** Block inference attacks by design
- All time slots submitted simultaneously (no iterative queries)
- Coordinator sees hashes, not times (can't ask "which hash is 9 AM?")
- Hash→time mapping only sent to user agents, never coordinator
- Stateless hashing service (can't correlate across meetings)

**What coordinator learns:** Which hash won, aggregate utility scores
**What coordinator cannot learn:** Actual times, who's busy when, final scheduled time

**Acceptable tradeoffs for v1:**
- Hashing service assumed honest-but-curious
- Coordinator could regenerate hashes (but still can't see availability)

**Non-issue:** Collusion between participants only reveals what they already know (that everyone attended the scheduled time). Aggregate scores are never shared, so utilities can't be back-calculated.
