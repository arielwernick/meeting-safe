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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
