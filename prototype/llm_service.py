"""
LLM Integration for Scheduling Intelligence

Supports two modes:
- "mock": Returns deterministic responses for testing
- "openai": Calls OpenAI API for real LLM reasoning
"""
from datetime import datetime
from typing import Optional
import json
import hashlib

from config import config
from models import CalendarEvent, MeetingRequest, SchedulingDecision


UTILITY_PROMPT_TEMPLATE = """You are a scheduling assistant for {user_name}.

NEW MEETING REQUEST:
- Title: {title}
- Organizer: {organizer}
- Type: {meeting_type}
- External: {external}
- Duration: {duration} minutes

YOUR CALENDAR FOR EACH TIME SLOT:
{slot_details}

LEARNED PREFERENCES FROM PAST DECISIONS:
{preferences}

INSTRUCTIONS:
For each time slot, output a utility score 0-100.
- 100 = perfect slot (free, preferred time)
- 70-99 = good slot (free, acceptable time)  
- 40-69 = willing to reschedule existing meeting for this
- 1-39 = reluctant but possible
- 0 = absolutely not (important conflict, external meeting, etc.)

Consider:
- User's learned preferences from past decisions
- Meeting importance (external > internal usually)
- Existing meeting importance
- Never reschedule external/customer meetings

Output JSON only:
{{
  "utilities": {{"slot_id": score, ...}},
  "reasoning": "brief explanation of key decisions"
}}"""


def build_slot_details(slots: list[dict]) -> str:
    """Format slot details for the prompt."""
    lines = []
    for slot in slots:
        if slot["status"] == "free":
            lines.append(f"- {slot['time']}: FREE")
        else:
            event = slot["conflict_event"]
            lines.append(
                f"- {slot['time']}: CONFLICT - \"{event['title']}\" "
                f"({event['event_type']}, importance {event['importance']}, "
                f"{'external' if event['external'] else 'internal'})"
            )
    return "\n".join(lines)


def build_preferences(decisions: list[SchedulingDecision]) -> str:
    """Extract preferences from decision history."""
    if not decisions:
        return "No past decisions recorded yet."
    
    lines = []
    for d in decisions:
        if d.user_action == "accepted":
            lines.append(f"- You ACCEPTED rescheduling {d.conflicting_type} for {d.meeting_type}")
        elif d.user_action == "rejected":
            lines.append(f"- You REJECTED rescheduling {d.conflicting_type} for {d.meeting_type}")
    
    return "\n".join(lines) if lines else "No clear preferences learned yet."


class MockLLM:
    """Deterministic mock LLM for testing."""
    
    def calculate_utilities(
        self,
        user_id: str,
        user_name: str,
        meeting_request: dict,
        slots: list[dict],
        decisions: list[dict]
    ) -> dict:
        """
        Mock utility calculation with realistic logic.
        
        Rules:
        - Free slots get base score 80
        - Morning (9-11) gets +10 bonus
        - External conflicts get 0 (never reschedule)
        - Internal conflicts:
          - Low importance (1-4): willing to reschedule (score 60)
          - Medium importance (5-7): reluctant (score 30)
          - High importance (8-10): protect (score 10)
        - Apply learned preferences from history
        """
        utilities = {}
        reasoning_parts = []
        
        # Build preference modifiers from history
        protect_types = set()
        reschedule_types = set()
        for d in decisions:
            if d.get("user_action") == "rejected" and d.get("conflicting_type"):
                protect_types.add(d["conflicting_type"])
            elif d.get("user_action") == "accepted" and d.get("conflicting_type"):
                reschedule_types.add(d["conflicting_type"])
        
        for slot in slots:
            slot_id = slot["hash"]
            time_obj = datetime.fromisoformat(slot["time"]) if isinstance(slot["time"], str) else slot["time"]
            hour = time_obj.hour
            
            if slot["status"] == "free":
                # Base score for free slot
                score = 80
                
                # Time of day preference
                if 9 <= hour <= 11:
                    score += 10
                    reasoning_parts.append(f"Morning slot {hour}:00 gets bonus")
                elif 12 <= hour <= 13:
                    score -= 10  # Lunch penalty
                
            else:
                # Conflict - evaluate if willing to reschedule
                event = slot["conflict_event"]
                
                # Never reschedule external meetings
                if event.get("external", False):
                    score = 0
                    reasoning_parts.append(f"Protecting external meeting at {hour}:00")
                else:
                    importance = event.get("importance", 5)
                    event_type = event.get("event_type", "meeting")
                    
                    # Check learned preferences
                    if event_type in protect_types:
                        score = 5
                        reasoning_parts.append(f"Learned: protect {event_type}")
                    elif event_type in reschedule_types:
                        score = 65
                        reasoning_parts.append(f"Learned: willing to reschedule {event_type}")
                    else:
                        # Default importance-based scoring
                        if importance <= 4:
                            score = 60
                        elif importance <= 7:
                            score = 30
                        else:
                            score = 10
                            reasoning_parts.append(f"High importance meeting at {hour}:00")
            
            utilities[slot_id] = score
        
        reasoning = "; ".join(reasoning_parts[:5]) if reasoning_parts else "Standard availability scoring"
        
        return {
            "utilities": utilities,
            "reasoning": reasoning
        }


class OpenAILLM:
    """Real OpenAI LLM integration."""
    
    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in config")
        
        from openai import OpenAI
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
    
    def calculate_utilities(
        self,
        user_id: str,
        user_name: str,
        meeting_request: dict,
        slots: list[dict],
        decisions: list[dict]
    ) -> dict:
        """Call OpenAI to calculate utilities."""
        
        # Build slot details
        slot_details = build_slot_details(slots)
        
        # Build preferences from history
        preferences = build_preferences([SchedulingDecision(**d) for d in decisions])
        
        # Build prompt
        prompt = UTILITY_PROMPT_TEMPLATE.format(
            user_name=user_name,
            title=meeting_request["title"],
            organizer=meeting_request["organizer_id"],
            meeting_type=meeting_request["meeting_type"],
            external=meeting_request["external"],
            duration=meeting_request["duration_minutes"],
            slot_details=slot_details,
            preferences=preferences
        )
        
        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a scheduling assistant. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result


def get_llm():
    """Factory function to get the appropriate LLM based on config."""
    if config.LLM_MODE == "openai":
        return OpenAILLM()
    else:
        return MockLLM()
