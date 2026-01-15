"""User Proxy Agent - Manages individual calendar and calculates utilities privately."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from database import CalendarEventDB, DecisionHistoryDB, UserDB
from llm_service import get_llm
from models import UtilityResponse


class UserProxyAgent:
    """
    Agent that runs on behalf of a single user.
    
    Responsibilities:
    - Knows user's calendar (private)
    - Calculates utilities for time slots
    - Learns from user's past decisions
    - Decides when to escalate
    """
    
    def __init__(self, user_id: str, db: Session):
        self.user_id = user_id
        self.db = db
        self.llm = get_llm()
        
        # Load user
        self.user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not self.user:
            raise ValueError(f"User {user_id} not found")
    
    def get_calendar(self, start: datetime, end: datetime) -> list[dict]:
        """Get calendar events in a time range."""
        events = self.db.query(CalendarEventDB).filter(
            CalendarEventDB.user_id == self.user_id,
            CalendarEventDB.start_time < end,
            CalendarEventDB.end_time > start
        ).all()
        
        return [
            {
                "id": e.id,
                "title": e.title,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "event_type": e.event_type,
                "external": e.external,
                "importance": e.importance,
                "recurring": e.recurring
            }
            for e in events
        ]
    
    def get_decision_history(self, limit: int = 10) -> list[dict]:
        """Get recent scheduling decisions for learning."""
        decisions = self.db.query(DecisionHistoryDB).filter(
            DecisionHistoryDB.user_id == self.user_id
        ).order_by(DecisionHistoryDB.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": d.id,
                "meeting_type": d.meeting_type,
                "conflicting_type": d.conflicting_type,
                "recommended_action": d.recommended_action,
                "user_action": d.user_action,
                "notes": d.notes
            }
            for d in decisions
        ]
    
    def get_conflict_at(self, time: datetime, duration_minutes: int) -> Optional[dict]:
        """Check if there's a calendar conflict at a specific time."""
        end_time = time + timedelta(minutes=duration_minutes)
        
        conflicts = self.db.query(CalendarEventDB).filter(
            CalendarEventDB.user_id == self.user_id,
            CalendarEventDB.start_time < end_time,
            CalendarEventDB.end_time > time
        ).all()
        
        if conflicts:
            # Return the most important conflict
            conflict = max(conflicts, key=lambda e: e.importance)
            return {
                "id": conflict.id,
                "title": conflict.title,
                "start_time": conflict.start_time.isoformat(),
                "end_time": conflict.end_time.isoformat(),
                "event_type": conflict.event_type,
                "external": conflict.external,
                "importance": conflict.importance,
                "recurring": conflict.recurring
            }
        return None
    
    def calculate_utilities(
        self,
        meeting_request: dict,
        hash_to_time: dict[str, str],
        duration_minutes: int
    ) -> UtilityResponse:
        """
        Calculate utility scores for each time slot.
        
        This is where the LLM magic happens - privately, on the user's side.
        """
        # Build slot details with conflict info
        slots = []
        for hash_val, time_str in hash_to_time.items():
            time = datetime.fromisoformat(time_str)
            conflict = self.get_conflict_at(time, duration_minutes)
            
            slots.append({
                "hash": hash_val,
                "time": time_str,
                "status": "conflict" if conflict else "free",
                "conflict_event": conflict
            })
        
        # Get decision history for learning
        decisions = self.get_decision_history()
        
        # Call LLM (mock or real)
        result = self.llm.calculate_utilities(
            user_id=self.user_id,
            user_name=self.user.name,
            meeting_request=meeting_request,
            slots=slots,
            decisions=decisions
        )

        # Normalize utilities keys: model may return time strings instead of hashes
        utilities = result.get("utilities", {})
        # hash_to_time is mapping hash->time (ISO string)
        time_to_hash = {v: k for k, v in hash_to_time.items()}
        normalized_utils: dict[str, int] = {}
        for key, score in utilities.items():
            # If key already a hash we expect
            if key in hash_to_time:
                normalized_utils[key] = score
            # If key is a time string, map to hash
            elif key in time_to_hash:
                normalized_utils[time_to_hash[key]] = score
            else:
                # Unknown key format - keep as-is
                normalized_utils[key] = score

        # Normalize slot_breakdown slot_id values similarly
        slot_breakdown = result.get("slot_breakdown", [])
        for slot in slot_breakdown:
            sid = slot.get("slot_id")
            # if slot_id is a time string, convert to hash
            if isinstance(sid, str) and sid in time_to_hash:
                slot["slot_id"] = time_to_hash[sid]
            # ensure a human-readable time field exists
            if "time" not in slot and slot.get("slot_id") in hash_to_time:
                slot["time"] = hash_to_time[slot["slot_id"]]

        escalate, reason = self._should_escalate(normalized_utils)

        return UtilityResponse(
            user_id=self.user_id,
            utilities=normalized_utils,
            escalate=escalate,
            escalation_reason=reason,
            reasoning=result.get("reasoning"),
            slot_breakdown=slot_breakdown,
            preferences_applied=result.get("preferences_applied", [])
        )
    
    def _should_escalate(self, utilities: dict[str, int]) -> tuple[bool, Optional[str]]:
        """Determine if we should escalate to the user."""
        scores = list(utilities.values())
        
        if not scores:
            return True, "No available slots"
        
        max_score = max(scores)
        
        # No good options
        if max_score < 40:
            return True, f"All slots have low scores (max: {max_score})"
        
        # Too close to call - top 2 within 10 points
        sorted_scores = sorted(scores, reverse=True)
        if len(sorted_scores) >= 2:
            if sorted_scores[0] - sorted_scores[1] < 10:
                return True, f"Multiple similar options (scores: {sorted_scores[0]}, {sorted_scores[1]})"
        
        return False, None
    
    def record_decision(
        self,
        meeting_type: str,
        conflicting_type: Optional[str],
        recommended_action: str,
        user_action: str,
        notes: Optional[str] = None
    ) -> None:
        """Record a scheduling decision for future learning."""
        import uuid
        
        decision = DecisionHistoryDB(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            timestamp=datetime.utcnow(),
            meeting_type=meeting_type,
            conflicting_type=conflicting_type,
            recommended_action=recommended_action,
            user_action=user_action,
            notes=notes
        )
        self.db.add(decision)
        self.db.commit()

    def get_learned_preferences(self) -> dict:
        """
        Derive preferences from decision history.
        
        Returns preferences like:
        - protect_events: event types the user never reschedules
        - reschedule_ok: event types the user is willing to move
        - preferred_times: morning, afternoon, etc.
        """
        decisions = self.get_decision_history(limit=50)
        
        protect_events = set()
        reschedule_ok = set()
        
        for d in decisions:
            if d.get("conflicting_type"):
                if d["user_action"] == "rejected":
                    # User protected this type of event
                    protect_events.add(d["conflicting_type"])
                elif d["user_action"] == "accepted":
                    # User was willing to reschedule this type
                    reschedule_ok.add(d["conflicting_type"])
        
        # User-specific default preferences (would come from profile in real system)
        user_prefs = {
            "alice": {
                "protect_events": ["customer_call", "external", "board_meeting"],
                "reschedule_ok": ["team_sync", "internal_1on1", "standup"],
                "preferred_times": ["morning"]
            },
            "bob": {
                "protect_events": ["focus_time", "deep_work", "external"],
                "reschedule_ok": ["standup", "team_sync"],
                "preferred_times": ["morning"]
            },
            "carol": {
                "protect_events": ["external", "customer_call"],
                "reschedule_ok": ["team_sync", "planning", "internal_1on1"],
                "preferred_times": ["afternoon"]
            }
        }
        
        defaults = user_prefs.get(self.user_id, {})
        
        return {
            "protect_events": list(protect_events) or defaults.get("protect_events", []),
            "reschedule_ok": list(reschedule_ok) or defaults.get("reschedule_ok", []),
            "preferred_times": defaults.get("preferred_times", [])
        }
