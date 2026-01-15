from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: str
    user_id: str
    title: str
    start_time: datetime
    end_time: datetime
    event_type: str  # "customer_call", "internal_1on1", "team_meeting", "focus_time"
    external: bool = False
    importance: int = 5  # 1-10
    recurring: bool = False


class MeetingRequest(BaseModel):
    id: str
    title: str
    organizer_id: str
    participant_ids: list[str]
    duration_minutes: int
    window_start: datetime
    window_end: datetime
    meeting_type: str = "internal"
    external: bool = False


class SchedulingDecision(BaseModel):
    id: str
    user_id: str
    timestamp: datetime
    meeting_type: str
    conflicting_type: Optional[str] = None
    recommended_action: str  # "schedule", "reschedule_existing"
    user_action: str  # "accepted", "rejected", "modified"
    notes: Optional[str] = None


class UtilityResponse(BaseModel):
    user_id: str
    utilities: dict[str, int]  # hash -> score (0-100)
    escalate: bool = False
    escalation_reason: Optional[str] = None
    reasoning: Optional[str] = None


class TimeSlot(BaseModel):
    time: datetime
    hash: str
    status: str  # "free", "conflict"
    conflict_event: Optional[CalendarEvent] = None


class User(BaseModel):
    id: str
    name: str
    email: str
