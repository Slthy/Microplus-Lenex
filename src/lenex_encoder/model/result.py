from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Result:
    """Represents a single swim performance (a <RESULT> element)."""
    resultid: str
    eventid: str
    swimtime: str
    heatid: Optional[str] = None
    lane: Optional[int] = None
    status: Optional[str] = None
    points: Optional[int] = 0
    reactiontime: Optional[float] = 0.0