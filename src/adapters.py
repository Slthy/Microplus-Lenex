from abc import ABC, abstractmethod
from typing import Dict, Optional
import requests
import json
import re
from pathlib import Path
from models import *
from utils import TimeUtils, FinaPoints, TeamCodeGenerator, InputValidator



class DataAdapter(ABC):
    """Abstract base class for data adapters."""
    
    @abstractmethod
    def scrape_data(self, source: str) -> None:
        """Scrape data from the source."""
        pass
    
    @abstractmethod
    def parse_competition(self) -> Competition:
        """Parse scraped data into Competition object."""
        pass
    
    @abstractmethod
    def validate_source(self, source: str) -> bool:
        """Validate that the source is correct for this adapter."""
        pass


class MicroplusAdapter(DataAdapter):
    """Adapter for Microplus timing system."""
    
    FILE_TYPES = {
        'SCH_D': 'schedules/by_date',
        'SCH_E': 'schedules/by_event',
        'STL1': 'startlists',
        'SUM': 'summary',
        'CGR1': 'results',
        'other': 'other'
    }
    
    RACE_CODES = {
        "50m Freestyle": "001",
        "100m Freestyle": "002",
        "200m Freestyle": "003",
        "400m Freestyle": "004",
        "800m Freestyle": "005",
        "1000m Freestyle": "006",
        "1500m Freestyle": "007",
        "3000m Freestyle": "008",
        "5000m Freestyle": "009",
        "50m Backstroke": "011",
        "100m Backstroke": "012",
        "200m Backstroke": "013",
        "50m Breaststroke": "016",
        "100m Breaststroke": "017",
        "200m Breaststroke": "018",
        "50m Butterfly": "026",
        "100m Butterfly": "027",
        "200m Butterfly": "028",
        "100m Individual Medley": "032",
        "200m Individual Medley": "033",
        "400m Individual Medley": "034",
        "4 x 50 m Freestyle": "041",
        "4 x 100m Freestyle": "042",
        "4 x 200m Freestyle": "043",
        "4 x 100 m Medley": "045"
    }
    
    RACE_TYPES = {
        "001": {'microplus': 'preliminary', 'lenex': 'PRE'},
        "002": {'microplus': 'spareggio', 'lenex': 'SOP'},
        "003": {'microplus': 'semifinals', 'lenex': 'SEM'},
        "004": {'microplus': 'spareggio2', 'lenex': 'SOS'},
        "005": {'microplus': 'final', 'lenex': 'FIN'},
        "006": {'microplus': 'young final', 'lenex': 'FIN'},
        "007": {'microplus': 'heats', 'lenex': 'TIM'}
    }
    
    STROKE_MAP = {
        'Freestyle': 'FREE',
        'Butterfly': 'FLY',
        'Breaststroke': 'BREAST',
        'Backstroke': 'BACK',
        'Individual Medley': 'MEDLEY',
        'Medley': 'MEDLEY'
    }
    
    JUNIOR_CATEGORIES = {
        "CAF": {'agemax': 17, 'agemin': 18},
        "CAM": {'agemax': 20, 'agemin': 19},
        "JUF": {'agemax': 15, 'agemin': 16},
        "JUM": {'agemax': 18, 'agemin': 17},
        "RAF": {'agemax': 13, 'agemin': 14},
        "RAM": {'agemax': 16, 'agemin': 14}
    }
    
    def __init__(self, data_dir: str = "scraped_data"):
        self.data_dir = Path(data_dir)
        self.url: Optional[str] = None
    
    def validate_source(self, source: str) -> bool:
        """Validate Microplus URL format."""
        pattern = r'https://fin\d{4}\.microplustiming\.com/NU_.*web\.php'
        return bool(re.match(pattern, source))
    
    def scrape_data(self, source: str) -> None:
        """Scrape data from Microplus system."""
        if not self.validate_source(source):
            raise ValueError("Invalid Microplus URL format")
        
        self.url = source
        url = source.replace('/NU', '/export/NU').replace('_web.php', '')
        
        # Get counter and file list
        counter_generale = requests.get(f'{url}/NU/CounterGenerale.json?').text[:-2]
        contatori = requests.get(
            f'{url}/NU/Contatori.json?x={counter_generale}'
        ).json()['contatori']
        
        # Download all JSON files
        for obj in contatori:
            scraped_data = requests.get(
                f'{url}/NU/{obj["nomefile"]}?x={obj["counter"]}'
            ).json()
            
            file_type = self.FILE_TYPES.get(obj['cod'], "other")
            file_path = self.data_dir / file_type
            file_path.mkdir(parents=True, exist_ok=True)
            
            with open(file_path / scraped_data["jsonfilename"], 'w') as f:
                json.dump(scraped_data, f)
    
    def parse_competition(self) -> Competition:
        """Parse Microplus data into Competition object."""
        parser = MicroplusParser(self.data_dir)
        return parser.parse()


class MicroplusParser:
    """Parses Microplus JSON data into domain models."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.adapter = MicroplusAdapter(str(data_dir))
    
    def parse(self) -> Competition:
        """Parse all data into Competition object."""
        
        # Get competition info from first result file
        results_dir = self.data_dir / 'results'
        first_result = next(results_dir.iterdir())
        
        with open(first_result, 'r') as f:
            data = json.load(f)
        
        # Determine pool length (would need user input in real scenario)
        pool_length_code = Course.LONG_COURSE  # Default, should be configurable
        
        # Create competition
        competition = Competition(
            name=data['Export']['ExpName'],
            city=data['Event']['Place'].split(',')[0],
            nation='ITA',  # Default, should be determined from city
            course=pool_length_code,
            pool=Pool(lane_min=0, lane_max=9)
        )
        
        pool_length = 50 if pool_length_code == Course.LONG_COURSE else 25
        
        # Parse sessions and events
        schedules_dir = self.data_dir / 'schedules' / 'by_date'
        event_id_counter = 1
        prelim_events = []  # Track preliminaries for linking to finals
        
        for session_file in sorted(schedules_dir.iterdir()):
            session_num = int(session_file.stem.split('_')[-1])
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Get session date/time from first event's result
            first_event_code = session_data['e'][0]
            result_filename = f"NU{first_event_code['c0']}" \
                            f"{self.adapter.RACE_CODES[first_event_code['d_en']]}" \
                            f"CLAS{first_event_code['c2'][::2]} 001.JSON"
            
            with open(results_dir / result_filename, 'r') as f:
                heat_data = json.load(f)
            
            session_date = datetime.strptime(
                heat_data['Heat']['UffDate'], 
                "%d/%m/%Y"
            ).date()
            
            session = Session(
                number=session_num,
                date=session_date,
                daytime=heat_data['Heat']['UffTime']
            )
            
            # Parse events in session
            for event_data in session_data['e']:
                event = self._parse_event(
                    event_data, 
                    event_id_counter, 
                    pool_length,
                    competition
                )
                
                # Track preliminaries for linking
                if event.round == Round.PRELIMINARY or event.round == Round.HEAT:
                    prelim_events.append({
                        'race_code': self.adapter.RACE_CODES[event_data['d_en']],
                        'event_id': event.event_id,
                        'category': event_data['c0']
                    })
                
                # Link finals to preliminaries
                if event.prev_event_id == "00":  # Needs linking
                    for prelim in prelim_events:
                        if (self.adapter.RACE_CODES[event_data['d_en']] == prelim['race_code']
                            and event_data['c0'] == prelim['category']):
                            event.prev_event_id = prelim['event_id']
                            break
                
                session.events.append(event)
                event_id_counter += 1
            
            competition.sessions.append(session)
        
        return competition
    
    def _parse_event(
        self, 
        event_data: Dict, 
        event_id: int, 
        pool_length: int,
        competition: Competition
    ) -> 'Event':
        """Parse a single event."""

        
        # Parse swimstyle
        swimstyle_split = event_data["d_en"].split('m')
        distance_str = swimstyle_split[0].strip()
        
        if 'x' in distance_str:
            distance = int(distance_str.replace('4 x ', ''))
            relay_count = 4
        else:
            distance = int(distance_str)
            relay_count = 1
        
        stroke_name = swimstyle_split[1].strip()
        stroke = Stroke[self.adapter.STROKE_MAP[stroke_name]]
        
        swimstyle = SwimStyle(
            distance=distance,
            stroke=stroke,
            relay_count=relay_count
        )
        
        # Determine gender
        gender_char = event_data['c0'][-1]
        if gender_char in ['M', 'F']:
            gender = Gender(gender_char)
        else:
            gender = Gender.MIXED
        
        # Determine round
        round_code = event_data['c2']
        round_type = self.adapter.RACE_TYPES.get(round_code, {}).get('lenex', 'PRE')
        round_enum = Round(round_type)
        
        # Create event
        event = Event(
            event_id=str(event_id),
            number=event_id,
            gender=gender,
            round=round_enum,
            swimstyle=swimstyle,
            daytime=event_data['h'],
            prev_event_id='-1' if round_code in ['001', '007'] else '00'
        )
        
        # Parse results and create heats, agegroups
        result_filename = f"NU{event_data['c0']}" \
                        f"{self.adapter.RACE_CODES[event_data['d_en']]}" \
                        f"CLAS{event_data['c2'][::2]} 001.JSON"
        
        results_dir = self.data_dir / 'results'
        with open(results_dir / result_filename, 'r') as f:
            heat_entries = json.load(f)
        
        # Create agegroup
        agegroup = self._create_agegroup(event_id, heat_entries, event_data)
        event.agegroups.append(agegroup)
        
        # Parse heats and results
        heats_dict = {}
        result_num = 1
        
        for entry in heat_entries['data']:
            heat_num = str(entry['b'])
            heat_id = f"{heat_num}000{event_id}"
            
            if heat_num not in heats_dict:
                heats_dict[heat_num] = Heat(
                    heat_id=heat_id,
                    number=heat_num,
                    daytime=heat_entries['Heat']['UffTime']
                )
            
            # Parse result based on relay or individual
            if swimstyle.is_relay:
                self._parse_relay_result(
                    entry, event, heat_id, result_num, 
                    agegroup, pool_length, competition
                )
            else:
                self._parse_individual_result(
                    entry, event, event_data, heat_id, result_num,
                    agegroup, pool_length, competition
                )
            
            result_num += 1
        
        # Add heats to event
        event.heats = list(heats_dict.values())
        
        return event
    
    def _create_agegroup(self, event_id: int, heat_entries: Dict, event_data: Dict) -> 'AgeGroup':  
        agegroup = AgeGroup(
            agegroup_id=f"10{event_id}",
            agemin=-1,
            agemax=-1
        )
        
        cat = heat_entries['Category']['Cod']
        
        if cat in self.adapter.JUNIOR_CATEGORIES:
            agegroup.agemax = self.adapter.JUNIOR_CATEGORIES[cat]['agemax']
            agegroup.agemin = self.adapter.JUNIOR_CATEGORIES[cat]['agemin']
        elif re.match(r'^\d\d[FM]$', cat):
            yob = int(f'20{cat[0]}{cat[1]}')
            agegroup.agemax = date.today().year - yob
            agegroup.agemin = date.today().year - yob - 1
        elif heat_entries["Round"]["Cod"] == "006":
            agegroup.agemax = 15
            agegroup.agemin = 18
        
        return agegroup
    
    def _parse_individual_result(
        self, entry: Dict, event: 'Event', event_data: Dict,
        heat_id: str, result_num: int, agegroup: 'AgeGroup',
        pool_length: int, competition: Competition
    ):
        """Parse individual result."""

        # Create athlete
        team = Team(
            name=entry['TeamDescrIta'],
            short_name=entry.get('TeamDescrItaVis', ''),
            code=TeamCodeGenerator.generate(entry['TeamDescrIta']),
            nation=entry['PlaNat']
        )
        
        athlete = Athlete(
            athlete_id=entry['PlaCod'],
            firstname=entry['PlaName'],
            lastname=entry['PlaSurname'],
            gender=Gender(event_data['c0'][-1]),
            birthdate=date(int(entry['PlaBirth']), 1, 1),
            team=team
        )
        
        competition.add_athlete(athlete)
        
        # Create entry
        entry_time = self._get_entry_time(event_data, entry['PlaCod'])
        athlete_entry = Entry(
            event_id=event.event_id,
            entry_time=entry_time,
            heat=str(entry['b']),
            lane=entry['PlaLane'],
            meet_info=datetime.strptime(
                entry.get('MemFields', [{}])[0].get('D', '01/01/2000'),
                "%d/%m/%Y"
            ).date() if entry.get('MemFields') else None
        )
        competition.add_entry(athlete.athlete_id, athlete_entry)
        
        # Parse splits
        splits = []
        for idx, time_data in enumerate(entry.get('MemFields', [])[1:], 1):
            if time_data.get('V', '') == "":
                break
            splits.append(Split(
                distance=pool_length * idx,
                swimtime=TimeUtils.format_time(time_data['V'])
            ))
        
        # Create result
        result_id = f"20{event.event_id}000{result_num}"
        swimtime = TimeUtils.format_time(entry['MemPrest'])
        
        result = Result(
            result_id=result_id,
            event_id=event.event_id,
            agegroup_id=agegroup.agegroup_id,
            place=entry['PlaCls'],
            swimtime=swimtime,
            heat=str(entry['b']),
            heat_id=heat_id,
            lane=entry['PlaLane'],
            splits=splits
        )
        
        # Calculate FINA points if valid time
        if swimtime != 'NT' and entry['PlaCls'].isdigit():
            result.points = str(FinaPoints.calculate(
                swimtime,
                event.swimstyle.distance,
                event.swimstyle.stroke.value,
                event.gender.value,
                'LCM' if pool_length == 50 else 'SCM'
            ))
        
        competition.add_result(athlete.athlete_id, result)
        
        # Add to agegroup rankings
        agegroup.rankings.append({
            'order': str(result_num),
            'place': entry['PlaCls'],
            'resultid': result_id
        })
    
    def _parse_relay_result(
        self, entry: Dict, event: 'Event', heat_id: str,
        result_num: int, agegroup: 'AgeGroup', 
        pool_length: int, competition: Competition
    ):
        
        team = Team(
            name=entry['TeamDescrIta'],
            short_name=entry.get('TeamDescrItaVis', ''),
            code=TeamCodeGenerator.generate(entry['TeamDescrIta']),
            nation=entry['PlaNat']
        )
        
        # Parse relay positions and splits
        positions = []
        all_splits = []
        
        for idx, player in enumerate(entry.get('Players', []), 1):
            athlete = Athlete(
                athlete_id=player['PlaCod'],
                firstname=player['PlaName'],
                lastname=player['PlaSurname'],
                gender=event.gender if event.gender != Gender.MIXED else Gender(player.get('PlaSex', 'M')),
                birthdate=date(int(player['PlaBirth']), 1, 1),
                team=team
            )
            
            competition.add_athlete(athlete)
            
            position = RelayPosition(
                number=idx,
                athlete=athlete,
                reaction_time=player.get('PlaRT', '')
            )
            positions.append(position)
            
            # Collect player splits
            for i in range(1, 5):
                split_time = player.get(f'PlaInt{i}', '')
                if split_time:
                    all_splits.append(TimeUtils.format_time(split_time))
        
        # Create cumulative splits
        splits = []
        for idx, split_time in enumerate(all_splits[:4], 1):  # Max 4 splits for relay
            if idx == 1:
                cumulative = split_time
            else:
                prev = splits[-1].swimtime
                cumulative = TimeUtils.add_times(prev, split_time, "00:00:00.00")
            
            splits.append(Split(
                distance=pool_length * idx,
                swimtime=cumulative
            ))
        
        # Create result
        result_id = f"20{event.event_id}{result_num}"
        result = Result(
            result_id=result_id,
            event_id=event.event_id,
            agegroup_id=agegroup.agegroup_id,
            place=entry['PlaCls'],
            swimtime=TimeUtils.format_time(entry['MemPrest']),
            heat=str(entry['b']),
            heat_id=heat_id,
            lane=entry['PlaLane'],
            splits=splits
        )
        
        competition.add_relay_result(team.code, result)
        
        # Create relay
        relay = Relay(
            team=team,
            gender=event.gender,
            positions=positions
        )
        competition.relays.append(relay)
        
        # Add to agegroup rankings
        agegroup.rankings.append({
            'order': str(result_num),
            'place': entry['PlaCls'],
            'resultid': result_id
        })
    
    def _get_entry_time(self, event_data: Dict, athlete_id: str) -> str:
        """Get entry time for athlete in event."""
        
        startlist_filename = f"NU{event_data['c0']}" \
                           f"{self.adapter.RACE_CODES[event_data['d_en']]}" \
                           f"STAR{event_data['c2'][::2]} 001.JSON"
        
        startlist_path = self.data_dir / 'startlists' / startlist_filename
        
        if not startlist_path.exists():
            return "NT"
        
        with open(startlist_path, 'r') as f:
            startlist = json.load(f)
        
        for entry in startlist.get('data', []):
            if entry.get('PlaCod') == athlete_id:
                return TimeUtils.format_time(entry.get('MemIscr', ''))
        
        return "NT"