"""
LLM Integration for Scheduling Intelligence

Supports two modes:
- "mock": Returns deterministic responses for testing
- "openai": Calls OpenAI API for real LLM reasoning

Key Feature: Rich explainability showing HOW preferences affect decisions.
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
  "reasoning": "brief explanation of key decisions",
  "slot_breakdown": [
    {{
      "slot_id": "hash",
      "score": 65,
      "decision": "WILLING_TO_RESCHEDULE or PROTECT or FREE",
      "factors": ["factor1", "factor2"]
    }}
  ]
}}"""""


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
    """
    Deterministic mock LLM for testing.
    
    Provides RICH EXPLAINABILITY showing exactly how preferences affect scoring.
    """
    
    def calculate_utilities(
        self,
        user_id: str,
        user_name: str,
        meeting_request: dict,
        slots: list[dict],
        decisions: list[dict]
    ) -> dict:
        """
        Mock utility calculation with realistic logic and rich explanations.
        
        Rules:
        - Free slots get base score 80
        - Morning (9-11) gets +10 bonus
        - External conflicts get 0 (never reschedule)
        - Internal conflicts:
          - Low importance (1-4): willing to reschedule (score 60)
          - Medium importance (5-7): reluctant (score 30)
          - High importance (8-10): protect (score 10)
        - Apply learned preferences from history
        
        Returns rich breakdown showing WHY each score was assigned.
        """
        utilities = {}
        reasoning_parts = []
        slot_breakdown = []
        preferences_applied = []
        
        # Build preference modifiers from history
        protect_types = {}  # type -> decision that caused it
        reschedule_types = {}  # type -> decision that caused it
        for d in decisions:
            if d.get("user_action") == "rejected" and d.get("conflicting_type"):
                protect_types[d["conflicting_type"]] = d
            elif d.get("user_action") == "accepted" and d.get("conflicting_type"):
                reschedule_types[d["conflicting_type"]] = d
        
        for slot in slots:
            slot_id = slot["hash"]
            time_obj = datetime.fromisoformat(slot["time"]) if isinstance(slot["time"], str) else slot["time"]
            hour = time_obj.hour
            time_str = time_obj.strftime("%I:%M %p")
            
            factors = []
            
            if slot["status"] == "free":
                # Base score for free slot
                base_score = 80
                score = base_score
                factors.append({
                    "type": "base_free",
                    "value": 80,
                    "reason": "Slot is free"
                })
                
                # Time of day preference
                if 9 <= hour <= 11:
                    score += 10
                    factors.append({
                        "type": "time_preference",
                        "value": +10,
                        "reason": "Morning slot (9-11 AM) preferred"
                    })
                    reasoning_parts.append(f"Morning slot {time_str} gets bonus")
                elif 12 <= hour <= 13:
                    score -= 10
                    factors.append({
                        "type": "time_preference", 
                        "value": -10,
                        "reason": "Lunch hour penalty"
                    })
                
                slot_breakdown.append({
                    "slot_id": slot_id,
                    "time": time_str,
                    "score": score,
                    "base_score": base_score,
                    "status": "FREE",
                    "conflict": None,
                    "factors": factors,
                    "decision": "AVAILABLE",
                    "decision_reason": f"No conflicts at {time_str}"
                })
                
            else:
                # Conflict - evaluate if willing to reschedule
                event = slot["conflict_event"]
                event_type = event.get("event_type", "meeting")
                importance = event.get("importance", 5)
                is_external = event.get("external", False)
                
                conflict_info = {
                    "title": event.get("title", "Unknown"),
                    "event_type": event_type,
                    "importance": importance,
                    "external": is_external
                }
                
                # Never reschedule external meetings
                if is_external:
                    score = 0
                    factors.append({
                        "type": "external_protection",
                        "value": 0,
                        "reason": f"NEVER reschedule external meeting: {event.get('title')}"
                    })
                    reasoning_parts.append(f"Protecting external meeting at {time_str}")
                    
                    slot_breakdown.append({
                        "slot_id": slot_id,
                        "time": time_str,
                        "score": 0,
                        "base_score": 0,
                        "status": "CONFLICT",
                        "conflict": conflict_info,
                        "factors": factors,
                        "decision": "PROTECT",
                        "decision_reason": "External/customer meetings are never rescheduled"
                    })
                else:
                    # Check learned preferences FIRST
                    if event_type in protect_types:
                        score = 5
                        source_decision = protect_types[event_type]
                        factors.append({
                            "type": "learned_preference",
                            "value": 5,
                            "reason": f"🧠 LEARNED: User previously REJECTED rescheduling {event_type}"
                        })
                        reasoning_parts.append(f"Learned: protect {event_type}")
                        preferences_applied.append({
                            "preference": f"protect_{event_type}",
                            "effect": "Score reduced to 5",
                            "source": f"User rejected rescheduling {event_type}"
                        })
                        
                        slot_breakdown.append({
                            "slot_id": slot_id,
                            "time": time_str,
                            "score": score,
                            "base_score": 0,
                            "status": "CONFLICT",
                            "conflict": conflict_info,
                            "factors": factors,
                            "decision": "PROTECT",
                            "decision_reason": f"Learned preference: user protects {event_type} meetings"
                        })
                        
                    elif event_type in reschedule_types:
                        score = 65
                        source_decision = reschedule_types[event_type]
                        factors.append({
                            "type": "learned_preference",
                            "value": 65,
                            "reason": f"🧠 LEARNED: User previously ACCEPTED rescheduling {event_type}"
                        })
                        reasoning_parts.append(f"Learned: willing to reschedule {event_type}")
                        preferences_applied.append({
                            "preference": f"reschedule_{event_type}",
                            "effect": "Score boosted to 65",
                            "source": f"User accepted rescheduling {event_type}"
                        })
                        
                        slot_breakdown.append({
                            "slot_id": slot_id,
                            "time": time_str,
                            "score": score,
                            "base_score": 0,
                            "status": "CONFLICT",
                            "conflict": conflict_info,
                            "factors": factors,
                            "decision": "WILLING_TO_RESCHEDULE",
                            "decision_reason": f"Learned preference: user accepts rescheduling {event_type}"
                        })
                    else:
                        # Default importance-based scoring
                        if importance <= 4:
                            score = 60
                            factors.append({
                                "type": "importance_score",
                                "value": 60,
                                "reason": f"Low importance ({importance}/10) - willing to reschedule"
                            })
                            decision = "WILLING_TO_RESCHEDULE"
                            decision_reason = f"Low importance meeting ({importance}/10)"
                        elif importance <= 7:
                            score = 30
                            factors.append({
                                "type": "importance_score",
                                "value": 30,
                                "reason": f"Medium importance ({importance}/10) - reluctant to reschedule"
                            })
                            decision = "RELUCTANT"
                            decision_reason = f"Medium importance meeting ({importance}/10)"
                        else:
                            score = 10
                            factors.append({
                                "type": "importance_score",
                                "value": 10,
                                "reason": f"High importance ({importance}/10) - strongly protect"
                            })
                            reasoning_parts.append(f"High importance meeting at {time_str}")
                            decision = "PROTECT"
                            decision_reason = f"High importance meeting ({importance}/10)"
                            
                        slot_breakdown.append({
                            "slot_id": slot_id,
                            "time": time_str,
                            "score": score,
                            "base_score": 0,
                            "status": "CONFLICT",
                            "conflict": conflict_info,
                            "factors": factors,
                            "decision": decision,
                            "decision_reason": decision_reason
                        })
            
            utilities[slot_id] = score
        
        reasoning = "; ".join(reasoning_parts[:5]) if reasoning_parts else "Standard availability scoring"
        
        return {
            "utilities": utilities,
            "reasoning": reasoning,
            "slot_breakdown": slot_breakdown,
            "preferences_applied": preferences_applied
        }


class OpenAILLM:
    """Real OpenAI LLM integration with rich explainability."""
    
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
        """Call OpenAI to calculate utilities with rich reasoning."""
        
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
                {"role": "system", "content": "You are a scheduling assistant. Output only valid JSON with utilities, reasoning, and slot_breakdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Ensure we have the expected structure
        if "preferences_applied" not in result:
            result["preferences_applied"] = []
        if "slot_breakdown" not in result:
            result["slot_breakdown"] = []
            
        return result


def get_llm():
    """Factory function to get the appropriate LLM based on config."""
    if config.LLM_MODE == "openai":
        return OpenAILLM()
    else:
        return MockLLM()
