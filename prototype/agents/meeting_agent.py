"""Meeting Agent - Coordinates scheduling across participants without seeing calendars."""
from datetime import datetime, timedelta
from typing import Optional
import uuid
from sqlalchemy.orm import Session

from database import MeetingDB, CalendarEventDB, UserDB
from agents.hashing_agent import hashing_agent
from agents.user_proxy_agent import UserProxyAgent
from models import MeetingRequest, UtilityResponse


class MeetingAgent:
    """
    Coordination agent that schedules meetings.
    
    Key privacy property: This agent NEVER sees:
    - Raw calendar data
    - Which times map to which hashes
    - The final scheduled time (only initiator learns this)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_time_slots(
        self,
        window_start: datetime,
        window_end: datetime,
        duration_minutes: int,
        interval_minutes: int = 30
    ) -> list[datetime]:
        """Generate all possible time slots in the scheduling window."""
        slots = []
        current = window_start
        
        while current + timedelta(minutes=duration_minutes) <= window_end:
            # Only schedule during business hours (9 AM - 5 PM)
            if 9 <= current.hour < 17:
                slots.append(current)
            current += timedelta(minutes=interval_minutes)
        
        return slots
    
    def coordinate_meeting(
        self,
        request: MeetingRequest
    ) -> dict:
        """
        Main coordination flow.
        
        Returns a detailed result showing:
        - What the Meeting Agent saw (hashes only)
        - Utilities from each participant
        - Aggregation results
        - Winning hash (not the time!)
        """
        meeting_id = request.id
        
        # Step 1: Generate all possible time slots
        times = self.generate_time_slots(
            request.window_start,
            request.window_end,
            request.duration_minutes
        )
        
        if not times:
            return {"error": "No valid time slots in window"}
        
        # Step 2: Get hashes from Hashing Agent
        hash_result = hashing_agent.generate_hashes(meeting_id, times)
        
        # Meeting Agent only sees the hashes, NOT the mapping
        hashes_only = hash_result["hashes"]
        hash_to_time = hash_result["mapping"]  # This goes to User Agents only
        
        # Step 3: Collect utilities from all participants
        all_participants = [request.organizer_id] + request.participant_ids
        participant_utilities: list[UtilityResponse] = []
        any_escalation = False
        
        for participant_id in all_participants:
            agent = UserProxyAgent(participant_id, self.db)
            utility_response = agent.calculate_utilities(
                meeting_request=request.model_dump(),
                hash_to_time=hash_to_time,
                duration_minutes=request.duration_minutes
            )
            participant_utilities.append(utility_response)
            
            if utility_response.escalate:
                any_escalation = True
        
        # Step 4: Aggregate utilities (weighted by role)
        aggregated = self._aggregate_utilities(
            participant_utilities,
            organizer_id=request.organizer_id
        )
        
        # Step 5: Find winning hash
        winning_hash = max(aggregated, key=aggregated.get)
        winning_score = aggregated[winning_hash]
        
        # Step 6: Build response
        # NOTE: We return the mapping for demo purposes
        # In production, only the initiator would receive this
        
        # Get top options for user choice (when escalating)
        sorted_options = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)
        top_options = [
            {
                "hash": h,
                "score": s,
                "time": hash_to_time[h]
            }
            for h, s in sorted_options[:3]  # Top 3 options
        ]
        
        return {
            "meeting_id": meeting_id,
            "status": "escalation_needed" if any_escalation else "scheduled",
            
            # What Meeting Agent sees (privacy demo)
            "meeting_agent_view": {
                "hashes": hashes_only,
                "participant_utilities": [
                    {
                        "user_id": u.user_id,
                        "utilities": u.utilities,
                        "reasoning": u.reasoning,
                        "slot_breakdown": u.slot_breakdown,
                        "preferences_applied": u.preferences_applied
                    }
                    for u in participant_utilities
                ],
                "aggregated_scores": aggregated,
                "winning_hash": winning_hash,
                "winning_score": winning_score
            },
            
            # What initiator can decrypt (only they have the mapping)
            "initiator_view": {
                "hash_to_time": hash_to_time,
                "winning_time": hash_to_time[winning_hash],
                "top_options": top_options  # For user choice on escalation
            },
            
            # Escalation info
            "escalations": [
                {
                    "user_id": u.user_id,
                    "reason": u.escalation_reason
                }
                for u in participant_utilities if u.escalate
            ]
        }
    
    def _aggregate_utilities(
        self,
        utilities: list[UtilityResponse],
        organizer_id: str
    ) -> dict[str, float]:
        """
        Aggregate utilities from all participants with weighting.
        
        Weights:
        - Organizer: 3.0
        - Required participants: 1.5
        - Optional: 1.0 (default)
        """
        # Collect all hashes
        all_hashes = set()
        for u in utilities:
            all_hashes.update(u.utilities.keys())
        
        # Aggregate with weights
        aggregated = {h: 0.0 for h in all_hashes}
        
        for u in utilities:
            weight = 3.0 if u.user_id == organizer_id else 1.5
            
            for hash_val, score in u.utilities.items():
                aggregated[hash_val] += score * weight
        
        return aggregated
    
    def finalize_meeting(
        self,
        meeting_id: str,
        winning_time: datetime,
        title: str,
        organizer_id: str,
        participant_ids: list[str],
        duration_minutes: int
    ) -> dict:
        """
        Finalize the meeting by creating calendar events.
        
        This would be called by the initiator after they decrypt the winning hash.
        """
        end_time = winning_time + timedelta(minutes=duration_minutes)
        
        # Create meeting record
        meeting = MeetingDB(
            id=meeting_id,
            title=title,
            organizer_id=organizer_id,
            start_time=winning_time,
            end_time=end_time,
            status="scheduled"
        )
        self.db.add(meeting)
        
        # Create calendar events for all participants
        all_participants = [organizer_id] + participant_ids
        for participant_id in all_participants:
            event = CalendarEventDB(
                id=f"{meeting_id}_{participant_id}",
                user_id=participant_id,
                title=title,
                start_time=winning_time,
                end_time=end_time,
                event_type="scheduled_meeting",
                external=False,
                importance=5,
                recurring=False
            )
            self.db.add(event)
        
        self.db.commit()
        
        return {
            "meeting_id": meeting_id,
            "title": title,
            "time": winning_time.isoformat(),
            "participants": all_participants,
            "status": "finalized"
        }
