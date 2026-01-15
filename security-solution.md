# Security Solution: Hash-Based Privacy for Multi-Agent Scheduling

## The Problem

LLM agents are iterative by nature. A naive scheduling agent will probe until it reconstructs your calendar:

```
Agent: "Free at 9?"    → No
Agent: "Free at 9:30?" → No
Agent: "Free at 10?"   → Yes
...calendar leaked
```

## The Solution

Three agents. No one sees what they don't need.

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
                    │    Meeting Agent       │
                    │  (sees hashes only,    │
                    │   never times)         │
                    └────────────┬───────────┘
                                 │
                                 │ winning hash
                                 ▼
                         ┌───────────────┐
                         │  Initiator    │
                         │  (decrypts,   │
                         │  sends invites)│
                         └───────────────┘
```

## How It Works

1. **Meeting Agent** generates time slots, sends to Hashing Agent
2. **Hashing Agent** returns hashes to Meeting Agent (no mapping), full mapping to User Agents
3. **User Agents** score each hash locally, send `{hash: utility}` pairs
4. **Meeting Agent** aggregates by hash, finds winner
5. **Initiator only** receives winning hash, decrypts to time, sends calendar invites

## What Each Party Knows

| Party | Knows | Doesn't Know |
|-------|-------|--------------|
| Meeting Agent | Winning hash, aggregate utilities | Actual times, who's busy when |
| User Agents | Own calendar, final time (via invite) | Other calendars, other utilities |
| Hashing Agent | Nothing (stateless) | Everything |

## Why It Works

- **No iterative queries:** All hashes sent at once
- **No time↔hash mapping for coordinator:** Can't ask "which hash is 9 AM?"
- **Initiator-only decryption:** Meeting Agent never learns the scheduled time
- **Stateless privacy layer:** Hashing Agent deletes after each request

## Attack Resistance

| Attack | Result |
|--------|--------|
| Coordinator iteratively probes availability | Blocked—all slots simultaneous |
| Coordinator correlates across meetings | Blocked—different hashes per meeting_id |
| Coordinator regenerates hashes | Limited—still can't see availability or final time |
| Participants collude | No leak—aggregate scores never shared |
