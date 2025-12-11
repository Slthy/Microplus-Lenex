from dataclasses import dataclass, field
from typing import List, Optional
from .athlete import Athlete

@dataclass
class Club:
    """Represents a <CLUB> element[cite: 213]."""
    name: str                 # The full name of the club [cite: 215]
    nation: str               # 3-letter nation code (e.g., 'USA') [cite: 215]
    code: Optional[str] = None  # Official club code [cite: 215]
    
    # Nested collection of athletes
    athletes: List[Athlete] = field(default_factory=list)
    
    # Helper method
    def add_athlete(self, athlete: Athlete):
        self.athletes.append(athlete)