from dataclasses import dataclass
from typing import Optional

@dataclass
class Heat:
    """
    Represents a <HEAT> element.
    Defines details for one heat (number, start time)[cite: 100].
    """
    
    # Required attributes
    heatid: str  # Mandatory, unique ID referenced by results [cite: 278]
    number: int  # The number of the heat [cite: 278]
    
    # Optional attributes
    daytime: Optional[str] = None      # Start time of the heat [cite: 278]
    agegroupid: Optional[str] = None # Reference to an age group [cite: 278]
    final: Optional[str] = None        # 'A', 'B', 'C', etc. for finals [cite: 278]
    order: Optional[int] = None        # Used for sorting if not by number [cite: 278]
    status: Optional[str] = None       # 'SEEDED', 'OFFICIAL', etc. [cite: 278]