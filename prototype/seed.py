"""Seed the database with sample users and calendar events."""
from datetime import datetime, timedelta
from database import SessionLocal, init_db, UserDB, CalendarEventDB, DecisionHistoryDB
import uuid


def seed_database():
    init_db()
    db = SessionLocal()
    
    # Clear existing data
    db.query(DecisionHistoryDB).delete()
    db.query(CalendarEventDB).delete()
    db.query(UserDB).delete()
    
    # Create users
    users = [
        UserDB(id="alice", name="Alice Chen", email="alice@company.com"),
        UserDB(id="bob", name="Bob Smith", email="bob@company.com"),
        UserDB(id="carol", name="Carol Jones", email="carol@company.com"),
    ]
    for user in users:
        db.add(user)
    
    # Base date: tomorrow
    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    # Alice's calendar - busy executive (packed day!)
    alice_events = [
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Morning Meditation",
            start_time=base + timedelta(hours=8),
            end_time=base + timedelta(hours=8, minutes=30),
            event_type="personal",
            external=False,
            importance=3,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Team Standup",
            start_time=base + timedelta(hours=9),
            end_time=base + timedelta(hours=9, minutes=30),
            event_type="team_meeting",
            external=False,
            importance=5,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Customer Call - Acme Corp",
            start_time=base + timedelta(hours=10),
            end_time=base + timedelta(hours=11),
            event_type="customer_call",
            external=True,
            importance=9,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Q1 Strategy Review",
            start_time=base + timedelta(hours=11),
            end_time=base + timedelta(hours=12),
            event_type="team_meeting",
            external=False,
            importance=7,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Lunch with Investor",
            start_time=base + timedelta(hours=12),
            end_time=base + timedelta(hours=13),
            event_type="external_meeting",
            external=True,
            importance=8,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="1:1 with Manager",
            start_time=base + timedelta(hours=14),
            end_time=base + timedelta(hours=14, minutes=30),
            event_type="manager_1on1",
            external=False,
            importance=7,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Product Review",
            start_time=base + timedelta(hours=15),
            end_time=base + timedelta(hours=16),
            event_type="team_meeting",
            external=False,
            importance=6,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            title="Board Prep Call",
            start_time=base + timedelta(hours=16, minutes=30),
            end_time=base + timedelta(hours=17),
            event_type="internal_meeting",
            external=False,
            importance=8,
            recurring=False
        ),
    ]
    
    # Bob's calendar - engineer with focus time blocks
    bob_events = [
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Email & Slack Catchup",
            start_time=base + timedelta(hours=8, minutes=30),
            end_time=base + timedelta(hours=9),
            event_type="admin",
            external=False,
            importance=3,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Focus Time - Feature Dev",
            start_time=base + timedelta(hours=9),
            end_time=base + timedelta(hours=11),
            event_type="focus_time",
            external=False,
            importance=6,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Code Review Session",
            start_time=base + timedelta(hours=11),
            end_time=base + timedelta(hours=12),
            event_type="team_meeting",
            external=False,
            importance=5,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Lunch Break",
            start_time=base + timedelta(hours=12),
            end_time=base + timedelta(hours=13),
            event_type="personal",
            external=False,
            importance=2,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Interview - Senior Eng",
            start_time=base + timedelta(hours=13),
            end_time=base + timedelta(hours=14),
            event_type="interview",
            external=True,
            importance=8,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Architecture Discussion",
            start_time=base + timedelta(hours=14),
            end_time=base + timedelta(hours=15),
            event_type="team_meeting",
            external=False,
            importance=6,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="1:1 with Alice",
            start_time=base + timedelta(hours=15),
            end_time=base + timedelta(hours=15, minutes=30),
            event_type="internal_1on1",
            external=False,
            importance=5,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="bob",
            title="Focus Time - Bug Fixes",
            start_time=base + timedelta(hours=16),
            end_time=base + timedelta(hours=17),
            event_type="focus_time",
            external=False,
            importance=6,
            recurring=True
        ),
    ]
    
    # Carol's calendar - PM with back-to-back meetings
    carol_events = [
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Daily Scrum",
            start_time=base + timedelta(hours=9),
            end_time=base + timedelta(hours=9, minutes=30),
            event_type="team_meeting",
            external=False,
            importance=5,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Sprint Planning",
            start_time=base + timedelta(hours=10),
            end_time=base + timedelta(hours=11, minutes=30),
            event_type="team_meeting",
            external=False,
            importance=8,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Stakeholder Update",
            start_time=base + timedelta(hours=12),
            end_time=base + timedelta(hours=12, minutes=30),
            event_type="external_meeting",
            external=True,
            importance=7,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Design Review",
            start_time=base + timedelta(hours=13),
            end_time=base + timedelta(hours=14),
            event_type="team_meeting",
            external=False,
            importance=6,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Vendor Call - Tools",
            start_time=base + timedelta(hours=14),
            end_time=base + timedelta(hours=15),
            event_type="vendor_call",
            external=True,
            importance=6,
            recurring=False
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Backlog Grooming",
            start_time=base + timedelta(hours=15, minutes=30),
            end_time=base + timedelta(hours=16, minutes=30),
            event_type="team_meeting",
            external=False,
            importance=5,
            recurring=True
        ),
        CalendarEventDB(
            id=str(uuid.uuid4()),
            user_id="carol",
            title="Customer Success Sync",
            start_time=base + timedelta(hours=16, minutes=30),
            end_time=base + timedelta(hours=17),
            event_type="internal_meeting",
            external=False,
            importance=5,
            recurring=True
        ),
    ]
    
    for event in alice_events + bob_events + carol_events:
        db.add(event)
    
    # Add some decision history for learning demonstration
    decisions = [
        DecisionHistoryDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            timestamp=datetime.now() - timedelta(days=5),
            meeting_type="customer_call",
            conflicting_type="internal_1on1",
            recommended_action="reschedule_existing",
            user_action="accepted",
            notes="Rescheduled 1:1 for customer call"
        ),
        DecisionHistoryDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            timestamp=datetime.now() - timedelta(days=3),
            meeting_type="internal_meeting",
            conflicting_type="manager_1on1",
            recommended_action="reschedule_existing",
            user_action="rejected",
            notes="User protected manager 1:1"
        ),
        DecisionHistoryDB(
            id=str(uuid.uuid4()),
            user_id="alice",
            timestamp=datetime.now() - timedelta(days=1),
            meeting_type="customer_call",
            conflicting_type="team_meeting",
            recommended_action="reschedule_existing",
            user_action="accepted",
            notes="Rescheduled team standup for customer"
        ),
    ]
    
    for decision in decisions:
        db.add(decision)
    
    db.commit()
    db.close()
    
    print("✅ Database seeded with sample data:")
    print("   - 3 users (Alice, Bob, Carol)")
    print("   - Calendar events for each user")
    print("   - Decision history for Alice (learning demo)")


if __name__ == "__main__":
    seed_database()
