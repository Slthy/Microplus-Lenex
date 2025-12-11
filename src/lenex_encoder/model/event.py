from dataclasses import dataclass, field
from typing import List, Optional
from .agegroup import AgeGroup
from .heat import Heat
from .swimstyle import Swimstyle

@dataclass
class Event:
    """Represents an <EVENT> element[cite: 245]."""

    # --- Required Attributes & Elements ---
    
    eventid: str      # Mandatory ID for referencing [cite: 246]
    number: int       # The event number 
    swimstyle: Swimstyle  # Describes distance, stroke, etc. 

    # --- Optional Attributes ---

    daytime: Optional[str] = None      # The start time of the event [cite: 246]
    gender: Optional[str] = 'A'        # 'M', 'F', 'X', or 'A' (default) [cite: 246]
    maxentries: Optional[int] = None   # Max entries per club in this event 
    order: Optional[int] = None        # Defines order of events if not by number 
    preveventid: Optional[str] = None  # Ref to a previous event id (e.g., prelims) 
    round: Optional[str] = 'TIM'       # 'TIM', 'FHT', 'FIN', 'SEM', 'PRE', etc. 
    timing: Optional[str] = None       # 'AUTOMATIC', 'MANUAL3', 'MANUAL1' 
    type: Optional[str] = None         # e.g., 'MASTERS' 

    # --- Optional Elements & Collections ---
    
    agegroups: List[AgeGroup] = field(default_factory=list) # Collection [cite: 246]
    heats: List[Heat] = field(default_factory=list)         # Collection [cite: 246]

    # --- Helper Methods ---

    def add_agegroup(self, agegroup: AgeGroup):
        self.agegroups.append(agegroup)
        
    def add_heat(self, heat: Heat):
        self.heats.append(heat)
