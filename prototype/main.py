"""
Meeting Safe - Privacy-Preserving Multi-Agent Meeting Scheduler

FastAPI Backend
"""
from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import config
from database import init_db, get_db, UserDB, CalendarEventDB, DecisionHistoryDB
from agents.meeting_agent import MeetingAgent
from agents.user_proxy_agent import UserProxyAgent
from models import MeetingRequest

app = FastAPI(
    title="Meeting Safe",
    description="Privacy-Preserving Multi-Agent Meeting Scheduler"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
from pathlib import Path
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/app")
def serve_app():
    return FileResponse(str(static_dir / "index.html"))

@app.get("/app/intelligence")
def serve_intelligence():
    return FileResponse(str(static_dir / "intelligence.html"))


# ============= Request/Response Models =============

class CreateMeetingRequest(BaseModel):
    title: str
    organizer_id: str
    participant_ids: list[str]
    duration_minutes: int = 30
    window_start: datetime
    window_end: datetime
    meeting_type: str = "internal"
    external: bool = False


class CreateEventRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    event_type: str = "meeting"
    external: bool = False
    importance: int = 5


class RecordDecisionRequest(BaseModel):
    meeting_type: str
    conflicting_type: Optional[str] = None
    recommended_action: str
    user_action: str  # "accepted", "rejected", "modified"
    notes: Optional[str] = None


# ============= API Endpoints =============

@app.on_event("startup")
def startup():
    init_db()
    # Auto-seed if database is empty
    from database import SessionLocal
    db = SessionLocal()
    try:
        user_count = db.query(UserDB).count()
        if user_count == 0:
            print("Database empty, seeding...")
            from seed import seed_database
            seed_database()
            print("Database seeded!")
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "service": "Meeting Safe", "llm_mode": config.LLM_MODE}


# ----- Users -----

@app.get("/api/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(UserDB).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


@app.get("/api/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}


# ----- Calendar -----

@app.get("/api/users/{user_id}/calendar")
def get_calendar(
    user_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get calendar events for a user."""
    if not start:
        start = datetime.now()
    if not end:
        end = start + timedelta(days=7)
    
    agent = UserProxyAgent(user_id, db)
    events = agent.get_calendar(start, end)
    return {"user_id": user_id, "events": events}


@app.post("/api/users/{user_id}/calendar")
def create_event(
    user_id: str,
    event: CreateEventRequest,
    db: Session = Depends(get_db)
):
    """Add an event to a user's calendar."""
    new_event = CalendarEventDB(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        event_type=event.event_type,
        external=event.external,
        importance=event.importance
    )
    db.add(new_event)
    db.commit()
    return {"id": new_event.id, "status": "created"}


# ----- Decision History (Learning) -----

@app.get("/api/users/{user_id}/decisions")
def get_decisions(user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get decision history for learning demo."""
    agent = UserProxyAgent(user_id, db)
    decisions = agent.get_decision_history(limit)
    return {"user_id": user_id, "decisions": decisions}


@app.post("/api/users/{user_id}/decisions")
def record_decision(
    user_id: str,
    decision: RecordDecisionRequest,
    db: Session = Depends(get_db)
):
    """Record a scheduling decision for future learning."""
    agent = UserProxyAgent(user_id, db)
    agent.record_decision(
        meeting_type=decision.meeting_type,
        conflicting_type=decision.conflicting_type,
        recommended_action=decision.recommended_action,
        user_action=decision.user_action,
        notes=decision.notes
    )
    return {"status": "recorded"}


@app.get("/api/users/{user_id}/preferences")
def get_preferences(user_id: str, db: Session = Depends(get_db)):
    """Get learned preferences for a user's agent."""
    agent = UserProxyAgent(user_id, db)
    preferences = agent.get_learned_preferences()
    return {"user_id": user_id, "preferences": preferences}


# ----- Meeting Scheduling -----

@app.post("/api/meetings/schedule")
def schedule_meeting(
    request: CreateMeetingRequest,
    db: Session = Depends(get_db)
):
    """
    Main scheduling endpoint.
    
    This demonstrates the full privacy-preserving flow:
    1. Generate time slots
    2. Hash the slots
    3. Collect utilities from each participant (privately)
    4. Aggregate and find winner
    5. Only initiator sees the winning time
    """
    meeting_request = MeetingRequest(
        id=str(uuid.uuid4()),
        title=request.title,
        organizer_id=request.organizer_id,
        participant_ids=request.participant_ids,
        duration_minutes=request.duration_minutes,
        window_start=request.window_start,
        window_end=request.window_end,
        meeting_type=request.meeting_type,
        external=request.external
    )
    
    agent = MeetingAgent(db)
    result = agent.coordinate_meeting(meeting_request)
    
    return result


@app.post("/api/meetings/{meeting_id}/finalize")
def finalize_meeting(
    meeting_id: str,
    winning_time: datetime,
    title: str,
    organizer_id: str,
    participant_ids: list[str],
    duration_minutes: int = 30,
    db: Session = Depends(get_db)
):
    """Finalize a meeting after user confirms the time."""
    agent = MeetingAgent(db)
    result = agent.finalize_meeting(
        meeting_id=meeting_id,
        winning_time=winning_time,
        title=title,
        organizer_id=organizer_id,
        participant_ids=participant_ids,
        duration_minutes=duration_minutes
    )
    return result


# ----- Demo Endpoints -----

@app.get("/api/demo/privacy-comparison")
def privacy_comparison(db: Session = Depends(get_db)):
    """
    Demo endpoint showing what each agent can see.
    
    This is for educational purposes to demonstrate the privacy model.
    """
    return {
        "traditional_scheduler": {
            "sees": "All calendars for all users",
            "learns": "Everyone's availability patterns",
            "risk": "Central point of data exposure"
        },
        "meeting_safe": {
            "meeting_agent_sees": "Only hashes and utility scores",
            "hashing_agent_sees": "Nothing (stateless)",
            "user_proxy_sees": "Only own calendar",
            "learns": "Individual preferences, privately"
        }
    }


@app.get("/api/demo/naive-vs-intelligent")
def naive_vs_intelligent_comparison(
    user_id: str = "alice",
    db: Session = Depends(get_db)
):
    """
    Demo endpoint showing the difference between naive and intelligent scheduling.
    
    Naive: Just checks if slot is free/busy
    Intelligent: Uses learned preferences to make smart tradeoffs
    """
    from datetime import datetime, timedelta
    
    agent = UserProxyAgent(user_id, db)
    
    # Get tomorrow's calendar
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    events = agent.get_calendar(tomorrow, tomorrow + timedelta(hours=12))
    decisions = agent.get_decision_history()
    
    # Build naive view (just busy/free)
    naive_slots = []
    intelligent_slots = []
    
    for hour in range(9, 17):  # 9 AM to 5 PM
        slot_time = tomorrow + timedelta(hours=hour)
        conflict = agent.get_conflict_at(slot_time, 30)
        
        if conflict:
            # Naive: just says BUSY
            naive_slots.append({
                "time": slot_time.strftime("%I:%M %p"),
                "status": "BUSY",
                "reason": f"Conflict with: {conflict['title']}"
            })
            
            # Intelligent: considers importance and learned preferences
            is_external = conflict.get("external", False)
            importance = conflict.get("importance", 5)
            event_type = conflict.get("event_type", "meeting")
            
            # Check learned preferences
            protect_types = {d["conflicting_type"] for d in decisions if d.get("user_action") == "rejected"}
            reschedule_types = {d["conflicting_type"] for d in decisions if d.get("user_action") == "accepted"}
            
            if is_external:
                intelligent_status = "PROTECT"
                intelligent_reason = "External meeting - never reschedule"
            elif event_type in protect_types:
                intelligent_status = "PROTECT"
                intelligent_reason = f"🧠 Learned: User protects {event_type}"
            elif event_type in reschedule_types:
                intelligent_status = "RESCHEDULE_OK"
                intelligent_reason = f"🧠 Learned: User accepts rescheduling {event_type}"
            elif importance <= 4:
                intelligent_status = "RESCHEDULE_OK"
                intelligent_reason = f"Low importance ({importance}/10)"
            elif importance <= 7:
                intelligent_status = "RELUCTANT"
                intelligent_reason = f"Medium importance ({importance}/10)"
            else:
                intelligent_status = "PROTECT"
                intelligent_reason = f"High importance ({importance}/10)"
            
            intelligent_slots.append({
                "time": slot_time.strftime("%I:%M %p"),
                "status": intelligent_status,
                "reason": intelligent_reason,
                "conflict": conflict["title"],
                "event_type": event_type,
                "importance": importance
            })
        else:
            # Both systems say FREE
            naive_slots.append({
                "time": slot_time.strftime("%I:%M %p"),
                "status": "FREE",
                "reason": "No conflict"
            })
            intelligent_slots.append({
                "time": slot_time.strftime("%I:%M %p"),
                "status": "FREE",
                "reason": "No conflict",
                "conflict": None
            })
    
    # Count available slots
    naive_available = sum(1 for s in naive_slots if s["status"] == "FREE")
    intelligent_available = sum(1 for s in intelligent_slots if s["status"] in ["FREE", "RESCHEDULE_OK"])
    
    return {
        "user_id": user_id,
        "comparison": {
            "naive": {
                "description": "Traditional scheduler - only sees busy/free",
                "available_slots": naive_available,
                "slots": naive_slots
            },
            "intelligent": {
                "description": "Meeting Safe - learns preferences, makes smart tradeoffs",
                "available_slots": intelligent_available,
                "slots": intelligent_slots,
                "preferences_used": [
                    {"type": "protect", "event_types": list({d["conflicting_type"] for d in decisions if d.get("user_action") == "rejected" and d.get("conflicting_type")})},
                    {"type": "reschedule_ok", "event_types": list({d["conflicting_type"] for d in decisions if d.get("user_action") == "accepted" and d.get("conflicting_type")})}
                ]
            }
        },
        "insight": f"Naive sees {naive_available} slots, Intelligent sees {intelligent_available} options (including smart rescheduling)"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
