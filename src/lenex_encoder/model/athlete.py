from dataclasses import dataclass, field
from typing import List
from .result import Result

@dataclass
class Athlete:
    """Represents an <ATHLETE> element."""
    athleteid: str
    firstname: str
    lastname: str
    gender: str
    birthdate: str
    results: List[Result] = field(default_factory=list)

    def add_result(self, result: Result):
        self.results.append(result)