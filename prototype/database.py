from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from config import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    
    events = relationship("CalendarEventDB", back_populates="user")
    decisions = relationship("DecisionHistoryDB", back_populates="user")


class CalendarEventDB(Base):
    __tablename__ = "calendar_events"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    event_type = Column(String, default="meeting")
    external = Column(Boolean, default=False)
    importance = Column(Integer, default=5)
    recurring = Column(Boolean, default=False)
    
    user = relationship("UserDB", back_populates="events")


class DecisionHistoryDB(Base):
    __tablename__ = "decision_history"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    meeting_type = Column(String)
    conflicting_type = Column(String, nullable=True)
    recommended_action = Column(String)
    user_action = Column(String)  # "accepted", "rejected", "modified"
    notes = Column(Text, nullable=True)
    
    user = relationship("UserDB", back_populates="decisions")


class MeetingDB(Base):
    __tablename__ = "meetings"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    organizer_id = Column(String, ForeignKey("users.id"))
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="pending")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
