from dataclasses import dataclass, field
from typing import List, Optional
from .ranking import Ranking

@dataclass
class AgeGroup:
    """
    Represents an <AGEGROUP> element[cite: 187].
    Contains the list of rankings for an event[cite: 25].
    """
    
    # Required attributes
    agemin: int  # The lower bound of the age range [cite: 188]
    agemax: int  # The upper bound of the age range [cite: 188]
    
    # Optional attributes
    agegroupid: Optional[str] = None # ID is needed to be referenced [cite: 188]
    name: Optional[str] = None       # e.g., "Juniors" [cite: 193]
    gender: Optional[str] = None     # 'M', 'F', or 'X' for mixed [cite: 188]
    calculate: Optional[str] = None  # 'SINGLE' or 'TOTAL' for relays [cite: 188]
    
    # Nested <RANKINGS> collection
    rankings: List[Ranking] = field(default_factory=list)