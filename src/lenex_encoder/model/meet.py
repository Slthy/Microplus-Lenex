from dataclasses import dataclass, field
from typing import List, Optional

# Original imports
from .session import Session
from .club import Club
from .athlete import Athlete

# Imports for new optional child elements
from .agedate import Agedate
from .contact import Contact
from .fees import Fees
from .pointtable import Pointtable
from .pool import Pool
from .qualify import Qualify


@dataclass
class Meet:
    """Represents a <MEET> element[cite: 313]."""
    
    # --- Required Attributes & Elements ---
    
    name: str  # The name of the meet [cite: 314]
    city: str  # The city where the meet is held [cite: 314]
    nation: str # 3-letter nation code [cite: 314]
    sessions: List[Session] = field(default_factory=list) # Description of all events [cite: 314]
    
    # --- Optional Attributes ---
    
    course: Optional[str] = None         # 'LCM', 'SCM'. Required if not in SESSION [cite: 314]
    altitude: Optional[int] = None       # Height above sea level [cite: 314]
    city_en: Optional[str] = None        # Name of meet city in english [cite: 314]
    deadline: Optional[str] = None       # Entry deadline date (YYYY-MM-DD) [cite: 314]
    deadlinetime: Optional[str] = None   # Entry deadline time (HH:MM) [cite: 314]
    entrystartdate: Optional[str] = None # Date when entries open [cite: 314]
    entrytype: Optional[str] = None      # 'OPEN' or 'INVITATION' [cite: 314]
    hostclub: Optional[str] = None       # Executing federation or club [cite: 314]
    hostclub_url: Optional[str] = None   # Website URL for host club [cite: 314]
    maxentries: Optional[int] = None     # Max entries per athlete/relay [cite: 314]
    name_en: Optional[str] = None        # Meet name in english [cite: 314]
    number: Optional[str] = None         # Sanction number for the meet [cite: 314]
    organizer: Optional[str] = None      # Promoting organisation (e.g., FINA) [cite: 314]
    organizer_url: Optional[str] = None  # Website URL for organizer [cite: 314]
    result_url: Optional[str] = None     # Direct link to result lists [cite: 314]
    state: Optional[str] = None          # Code of the state of the meet city [cite: 314]
    swrid: Optional[str] = None          # Global unique meet id from swimrankings.net [cite: 314]
    timing: Optional[str] = None         # 'AUTOMATIC', 'MANUAL3', 'MANUAL1' [cite: 318]
    type: Optional[str] = None           # Meet type (default is for FINA rules) [cite: 318]
    
    # --- Optional Elements & Collections ---
    
    agedate: Optional[Agedate] = None       # The date used to calculate athlete ages [cite: 314]
    contact: Optional[Contact] = None       # Contact address for the meet organizer [cite: 314]
    fees: Optional[Fees] = None             # Collection of global fees [cite: 314, 265]
    pointtable: Optional[Pointtable] = None # Description of the point table used [cite: 314, 346]
    pool: Optional[Pool] = None             # Details about the pool [cite: 314, 349]
    qualify: Optional[Qualify] = None       # Details about qualification times [cite: 314, 356]
    clubs: List[Club] = field(default_factory=list) # Collection of clubs [cite: 314]

    # --- Helper methods (unchanged) ---
    
    def add_session(self, session: Session):
        self.sessions.append(session)
        
    def add_club(self, club: Club):
        self.clubs.append(club)
        
    def find_athlete(self, athlete_id: str) -> Optional[Athlete]:
        """Helper to find an athlete across all clubs."""
        for club in self.clubs:
            for athlete in club.athletes:
                if athlete.athleteid == athlete_id:
                    return athlete
        return None