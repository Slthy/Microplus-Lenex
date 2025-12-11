from dataclasses import dataclass

@dataclass
class Ranking:
    """Represents a <RANKING> element."""
    place: int      # The final position/rank
    resultid: str   # The ID linking to the <RESULT> element