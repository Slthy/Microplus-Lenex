from dataclasses import dataclass, field
from typing import Optional
from typing import List
from .event import Event

@dataclass
class Session:
    """Represents a <SESSION> element[cite: 450]."""
    number: int             # The unique session number [cite: 452]
    date: str               # The date of the session, e.g., "YYYY-MM-DD" [cite: 452]
    daytime: Optional[str] = None  # Start time, e.g., "HH:MM" [cite: 452]
    name: Optional[str] = None     # e.g., "Day 1 - Prelims" [cite: 452]
    
    # Nested collection of events
    events: List[Event] = field(default_factory=list)
    
    # Helper method
    def add_event(self, event: Event):
        self.events.append(event)