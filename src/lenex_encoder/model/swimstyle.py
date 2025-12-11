from dataclasses import dataclass
from typing import Optional

@dataclass
class Swimstyle:
    """
    Represents a <SWIMSTYLE> element[cite: 471].
    Describes the distance, stroke, and style of an event.
    """
    
    # Required attributes
    distance: int   # The distance for the event [cite: 472]
    relaycount: int # 1 for individual, >1 for relay [cite: 472]
    stroke: str     # 'FREE', 'BACK', 'BREAST', 'FLY', 'MEDLEY' [cite: 472]
    
    # Optional attributes
    technique: Optional[str] = None  # 'KICK', 'PULL', etc. [cite: 472]
    name: Optional[str] = None       # Name if stroke is 'UNKNOWN' [cite: 472]
    code: Optional[str] = None       # Code if stroke is 'UNKNOWN' [cite: 472]
    swimstyleid: Optional[str] = None # ID if stroke is 'UNKNOWN' [cite: 472]