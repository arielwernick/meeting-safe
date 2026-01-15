"""Hashing Agent - Provides cryptographic privacy through deterministic hashing."""
import hashlib
from datetime import datetime


class HashingAgent:
    """
    Stateless hashing service.
    
    Creates deterministic hashes for time slots so that:
    - Same meeting_id + time = same hash (for intersection)
    - Meeting Agent sees only hashes, not times
    - User Agents receive the full hash→time mapping
    """
    
    def hash_time(self, meeting_id: str, time: datetime) -> str:
        """Generate a deterministic hash for a meeting_id + time combination."""
        time_str = time.isoformat()
        data = f"{meeting_id}||{time_str}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]  # Truncate for readability
    
    def generate_hashes(
        self,
        meeting_id: str,
        times: list[datetime]
    ) -> dict:
        """
        Generate hashes for all time slots.
        
        Returns:
            {
                "hashes": ["abc123...", "def456...", ...],  # For Meeting Agent (no mapping)
                "mapping": {"abc123...": "2026-01-16T09:00:00", ...}  # For User Agents
            }
        """
        mapping = {}
        for time in times:
            hash_val = self.hash_time(meeting_id, time)
            mapping[hash_val] = time.isoformat()
        
        return {
            "hashes": list(mapping.keys()),
            "mapping": mapping
        }


# Singleton instance
hashing_agent = HashingAgent()
