"""
Domain models for swimming competition data.
These classes represent the core business entities.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime, date
from enum import Enum


class Gender(Enum):
    MALE = "M"
    FEMALE = "F"
    MIXED = "X"


class Stroke(Enum):
    FREE = "FREE"
    BACK = "BACK"
    BREAST = "BREAST"
    FLY = "FLY"
    MEDLEY = "MEDLEY"


class Round(Enum):
    PRELIMINARY = "PRE"
    SEMIFINAL = "SEM"
    FINAL = "FIN"
    HEAT = "TIM"
    SWIM_OFF = "SOP"


class Course(Enum):
    SHORT_COURSE = "SCM"
    LONG_COURSE = "LCM"


@dataclass
class Split:
    """Represents a split time at a specific distance."""
    distance: int
    swimtime: str  # Format: HH:MM:SS.ss
    
    def __post_init__(self):
        if not isinstance(self.distance, int):
            self.distance = int(self.distance)


@dataclass
class Contact:
    """Contact information."""
    name: str = ""
    city: str = ""
    zip_code: str = ""
    country: str = ""
    email: str = ""
    internet: str = ""


@dataclass
class Team:
    """Represents a club/team."""
    name: str
    code: str
    nation: str
    type: str = "CLUB"
    short_name: Optional[str] = None
    contact: Optional[Contact] = None
    
    def __hash__(self):
        return hash(self.code)


@dataclass
class Athlete:
    """Represents an individual athlete."""
    athlete_id: str
    firstname: str
    lastname: str
    gender: Gender
    birthdate: date
    team: Team
    
    def __hash__(self):
        return hash(self.athlete_id)
    
    def __eq__(self, other):
        if not isinstance(other, Athlete):
            return False
        return self.athlete_id == other.athlete_id


@dataclass
class Entry:
    """Represents an entry in an event."""
    event_id: str
    entry_time: str = "NT"
    heat: Optional[str] = None
    lane: Optional[str] = None
    meet_info: Optional[date] = None


@dataclass
class Result:
    """Represents a result in an event."""
    result_id: str
    event_id: str
    agegroup_id: str
    place: str
    swimtime: str
    heat: str
    heat_id: str
    lane: str
    reaction_time: str = ""
    points: str = ""
    splits: List[Split] = field(default_factory=list)


@dataclass
class RelayPosition:
    """Represents an athlete's position in a relay."""
    number: int
    athlete: Athlete
    reaction_time: str = ""


@dataclass
class Relay:
    """Represents a relay team."""
    team: Team
    gender: Gender
    number: int = 1
    agemin: int = -1
    agemax: int = -1
    positions: List[RelayPosition] = field(default_factory=list)
    
    
@dataclass
class Heat:
    """Represents a heat in an event."""
    heat_id: str
    number: str
    daytime: str


@dataclass
class AgeGroup:
    """Represents an age group in an event."""
    agegroup_id: str
    agemin: int = -1
    agemax: int = -1
    rankings: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SwimStyle:
    """Represents the swimming style of an event."""
    distance: int
    stroke: Stroke
    relay_count: int = 1
    
    @property
    def is_relay(self) -> bool:
        return self.relay_count > 1


@dataclass
class Event:
    """Represents a swimming event."""
    event_id: str
    number: int
    gender: Gender
    round: Round
    swimstyle: SwimStyle
    daytime: str
    prev_event_id: Optional[str] = "-1"
    agegroups: List[AgeGroup] = field(default_factory=list)
    heats: List[Heat] = field(default_factory=list)
    
    @property
    def is_relay(self) -> bool:
        return self.swimstyle.is_relay


@dataclass
class Session:
    """Represents a competition session."""
    number: int
    date: date
    daytime: str
    events: List[Event] = field(default_factory=list)


@dataclass
class Pool:
    """Represents a swimming pool."""
    lane_min: int = 0
    lane_max: int = 9


@dataclass
class Competition:
    """Represents a swimming competition (meet)."""
    name: str
    city: str
    nation: str
    course: Course
    timing: str = "AUTOMATIC"
    pool: Pool = field(default_factory=Pool)
    sessions: List[Session] = field(default_factory=list)
    clubs: Dict[str, Team] = field(default_factory=dict)
    athletes: Dict[str, Athlete] = field(default_factory=dict)
    relays: List[Relay] = field(default_factory=list)
    
    # Athlete entries and results indexed by athlete_id
    athlete_entries: Dict[str, List[Entry]] = field(default_factory=dict)
    athlete_results: Dict[str, List[Result]] = field(default_factory=dict)
    
    # Relay results
    relay_results: Dict[str, List[Result]] = field(default_factory=dict)
    
    def add_athlete(self, athlete: Athlete):
        """Add an athlete to the competition."""
        self.athletes[athlete.athlete_id] = athlete
        if athlete.team.code not in self.clubs:
            self.clubs[athlete.team.code] = athlete.team
    
    def add_entry(self, athlete_id: str, entry: Entry):
        """Add an entry for an athlete."""
        if athlete_id not in self.athlete_entries:
            self.athlete_entries[athlete_id] = []
        self.athlete_entries[athlete_id].append(entry)
    
    def add_result(self, athlete_id: str, result: Result):
        """Add a result for an athlete."""
        if athlete_id not in self.athlete_results:
            self.athlete_results[athlete_id] = []
        self.athlete_results[athlete_id].append(result)
    
    def add_relay_result(self, team_code: str, result: Result):
        """Add a result for a relay."""
        if team_code not in self.relay_results:
            self.relay_results[team_code] = []
        self.relay_results[team_code].append(result)