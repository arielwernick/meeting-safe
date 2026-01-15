# Security Model: Hash-Based Privacy

## The Threat Model

### What We're Protecting Against

1. **Curious Coordinators**: A Meeting Agent that tries to learn calendar patterns
2. **Inference Attacks**: Sequential probing to reconstruct calendars
3. **Cross-Meeting Correlation**: Linking availability across multiple scheduling requests
4. **Data Accumulation**: Building profiles from aggregated scheduling data

### What We're NOT Protecting Against (v1)

1. **Malicious User Agents**: Users could lie about their availability
2. **Timing Attacks**: Sophisticated attacks on hash computation time
3. **Collusion with Majority**: If N-1 participants collude, they learn the Nth person's availability

---

## Attack Resistance Matrix

| Attack Vector | Traditional Scheduler | Meeting Safe |
|---------------|----------------------|--------------|
| Coordinator sees all calendars | ✗ Full visibility | ✓ Sees only hashes |
| Iterative availability probing | ✗ Can reconstruct calendar | ✓ Blocked—all slots simultaneous |
| Cross-meeting correlation | ✗ Same times, same data | ✓ Different hashes per meeting_id |
| Learns final scheduled time | ✗ Yes | ✓ Only initiator knows |
| Participant collusion | ✗ Can share | ⚠️ Can share—but only reveals what they already know |

---

## How Each Attack Is Blocked

### 1. No Iterative Queries

**The Attack**: 
```
Agent: "Are you free at 9?"     → "No"
Agent: "Are you free at 9:30?"  → "No"  
Agent: "Are you free at 10?"    → "Yes"
// Repeat 16 times → full calendar reconstructed
```

**Our Defense**:
All time slots are hashed and sent in a single batch. User Agents return utilities for ALL slots simultaneously. There's no back-and-forth to exploit.

### 2. No Time↔Hash Mapping for Coordinator

**The Attack**:
Coordinator regenerates hashes to decode times.

**Our Defense**:
Hashing Agent sends hashes to Meeting Agent WITHOUT the mapping. Even if Meeting Agent runs SHA256 itself, it doesn't know which times were in the original set.

```python
# Meeting Agent receives:
hashes = ["abc123...", "def456...", "ghi789..."]

# Meeting Agent does NOT receive:
mapping = {"abc123": "9:00am", "def456": "9:30am", ...}  # ❌
```

### 3. No Cross-Meeting Correlation

**The Attack**:
Track that hash_abc always gets low utility from Alice → infer it's when she's busy.

**Our Defense**:
Hashes include meeting_id:
```python
hash = SHA256(f"{meeting_id}||{time}")
```

Same time, different meetings → different hashes. No correlation possible.

### 4. Initiator-Only Decryption

**The Attack**:
Coordinator collects all scheduled times → builds availability profiles.

**Our Defense**:
Meeting Agent returns only the winning hash to the initiator. The initiator decrypts locally and sends calendar invites directly. **Meeting Agent never learns the final time.**

---

## Trust Assumptions

### Hashing Agent: Honest-but-Curious

We assume the Hashing Agent:
- ✓ Executes the hashing algorithm correctly
- ✓ Sends correct mappings to User Agents
- ⚠️ Might try to learn from data it sees

**Mitigation**: Hashing Agent is stateless—it deletes all data after each request. Even if compromised, it only sees times for one meeting at a time.

### Meeting Agent: Honest-but-Curious

We assume the Meeting Agent:
- ✓ Aggregates utilities correctly
- ✓ Sends winning hash to correct initiator
- ⚠️ Might try to learn from hashes and utilities

**What it CAN'T learn**:
- Which hash corresponds to which time
- Who's busy at which times
- The final scheduled time

### User Agents: Trusted by Their User

Each User Agent is trusted only by its own user. If Alice's Agent is malicious, it can only harm Alice's scheduling—not Bob's or Carol's.

---

## Collusion Analysis

### Scenario: Alice and Bob Collude

Alice and Bob could share:
- Their own hash→time mappings (identical, by design)
- Their utility scores
- The final scheduled time (Alice knows if she's initiator)

**Result**: They learn nothing new. They already knew:
- Their own availability
- The final meeting time (from the calendar invite)

They still DON'T learn:
- Carol's availability pattern
- Carol's utility scores

### Scenario: Coordinator + Hashing Agent Collude

If both are compromised:
- They have hashes AND mapping
- They can decode which times are being considered

**What they still DON'T know**:
- Individual user availability (only aggregate utility)
- Who specifically is busy when (scores are bucketed by hash)

---

## Future Hardening (v2+)

### Secure Multi-Party Computation

Replace simple hashing with MPC protocols:
- Users compute on encrypted data
- Coordinator never sees even utilities
- Requires more infrastructure

### Differential Privacy

Add noise to utility scores:
- Individual preferences masked
- Aggregate still useful
- Harder to reverse-engineer

### Zero-Knowledge Proofs

User Agents prove:
- "This utility is correctly computed from my calendar"
- Without revealing the calendar

---

## Security Checklist

| Property | Status | Notes |
|----------|--------|-------|
| Calendar data never leaves user agent | ✓ | Core invariant |
| Coordinator can't map hashes to times | ✓ | Mapping only sent to user agents |
| No iterative probing | ✓ | All slots simultaneous |
| Cross-meeting correlation blocked | ✓ | meeting_id in hash |
| Coordinator doesn't learn final time | ✓ | Initiator-only decryption |
| Stateless privacy layer | ✓ | Hashing agent deletes after each request |

---

## References

- [Architecture Overview](architecture.md) - Full system design
- [Intelligence & Learning](intelligence.md) - How LLM fits in securely
