"""
Encoders for converting Competition data to various formats.
"""
from abc import ABC, abstractmethod
import xml.etree.cElementTree as ET
import xml.dom.minidom
from pathlib import Path
from models import Competition
from urllib.parse import unquote


class Encoder(ABC):
    """Abstract base class for encoders."""
    
    @abstractmethod
    def encode(self, competition: Competition) -> str:
        """Encode competition data to target format."""
        pass
    
    @abstractmethod
    def save(self, data: str, filename: str, output_dir: str = "processed_data") -> None:
        """Save encoded data to file."""
        pass


class LenexEncoder(Encoder):
    """
    Encodes Competition data to LENEX 3.0 XML format.
    
    LENEX is the standard format for swimming competition data.
    Specification: https://wiki.swimrankings.net/images/6/62/Lenex_3.0_Technical_Documentation.pdf
    """
    
    VERSION = "3.0"
    CONSTRUCTOR_NAME = "Microplus Informatica Srl - Encoded By Alessandro Borsato's LEnexENcoder"
    CONSTRUCTOR_VERSION = "2.0"
    
    def __init__(self):
        self.root = None
    
    def encode(self, competition: Competition) -> str:
        """
        Encode competition data to LENEX XML.
        
        Args:
            competition: Competition object with all data
            
        Returns:
            XML string in LENEX format
        """
        self._build_xml_tree(competition)
        return self._format_xml()
    
    def _build_xml_tree(self, competition: Competition) -> None:
        """Build the XML tree structure."""
        # Root element
        self.root = ET.Element("LENEX", version=self.VERSION)
        
        # Constructor info
        self._add_constructor()
        
        # Meets collection
        meets = ET.SubElement(self.root, "MEETS")
        meet = ET.SubElement(meets, "MEET", {
            'name': competition.name,
            'city': competition.city,
            'nation': competition.nation,
            'course': competition.course.value,
            'timing': competition.timing
        })
        
        # Pool info
        ET.SubElement(meet, "POOL", {
            'lanemin': str(competition.pool.lane_min),
            'lanemax': str(competition.pool.lane_max)
        })
        
        # Point table
        ET.SubElement(meet, "POINTTABLE", {
            'name': 'FINA Point Scoring',
            'version': '2023'
        })
        
        # Sessions
        self._add_sessions(meet, competition)
        
        # Clubs and athletes
        self._add_clubs(meet, competition)
    
    def _add_constructor(self) -> None:
        """Add constructor information to XML."""
        constructor = ET.SubElement(self.root, "CONSTRUCTOR", {
            'name': self.CONSTRUCTOR_NAME,
            'registration': self.CONSTRUCTOR_NAME,
            'version': self.CONSTRUCTOR_VERSION
        })
        
        ET.SubElement(constructor, "CONTACT", {
            'name': self.CONSTRUCTOR_NAME,
            'zip': 'IT-12030',
            'city': 'Marene',
            'country': 'ITA',
            'email': 'info@system.com',
            'internet': 'https://www.system.com'
        })
    
    def _add_sessions(self, meet: ET.Element, competition: Competition) -> None:
        """Add sessions and events to meet."""
        sessions_elem = ET.SubElement(meet, "SESSIONS")
        
        for session in competition.sessions:
            session_elem = ET.SubElement(sessions_elem, "SESSION", {
                'number': str(session.number),
                'date': session.date.strftime("%Y-%m-%d"),
                'daytime': session.daytime
            })
            
            events_elem = ET.SubElement(session_elem, "EVENTS")
            
            for event in session.events:
                self._add_event(events_elem, event)
    
    def _add_event(self, events_elem: ET.Element, event) -> None:
        """Add a single event to events collection."""
        event_elem = ET.SubElement(events_elem, "EVENT", {
            'number': str(event.number),
            'eventid': event.event_id,
            'preveventid': event.prev_event_id,
            'gender': event.gender.value,
            'round': event.round.value,
            'daytime': event.daytime
        })
        
        # Swimstyle
        ET.SubElement(event_elem, "SWIMSTYLE", {
            'distance': str(event.swimstyle.distance),
            'relaycount': str(event.swimstyle.relay_count),
            'stroke': event.swimstyle.stroke.value
        })
        
        # Agegroups
        agegroups_elem = ET.SubElement(event_elem, "AGEGROUPS")
        
        for agegroup in event.agegroups:
            agegroup_elem = ET.SubElement(agegroups_elem, "AGEGROUP", {
                'agegroupid': agegroup.agegroup_id,
                'agemax': str(agegroup.agemax),
                'agemin': str(agegroup.agemin)
            })
            
            # Rankings
            if agegroup.rankings:
                rankings_elem = ET.SubElement(agegroup_elem, "RANKINGS")
                for ranking in agegroup.rankings:
                    ET.SubElement(rankings_elem, "RANKING", ranking)
        
        # Heats
        if event.heats:
            heats_elem = ET.SubElement(event_elem, "HEATS")
            for heat in event.heats:
                ET.SubElement(heats_elem, "HEAT", {
                    'daytime': heat.daytime,
                    'heatid': heat.heat_id,
                    'number': heat.number
                })
    
    def _add_clubs(self, meet: ET.Element, competition: Competition) -> None:
        """Add clubs, athletes, and results to meet."""
        clubs_elem = ET.SubElement(meet, "CLUBS")
        
        # Group athletes by club
        athletes_by_club = {}
        for athlete_id, athlete in competition.athletes.items():
            club_code = athlete.team.code
            if club_code not in athletes_by_club:
                athletes_by_club[club_code] = []
            athletes_by_club[club_code].append(athlete)
        
        # Group relays by club
        relays_by_club = {}
        for relay in competition.relays:
            club_code = relay.team.code
            if club_code not in relays_by_club:
                relays_by_club[club_code] = []
            relays_by_club[club_code].append(relay)
        
        # Add clubs
        for club_code, team in competition.clubs.items():
            club_elem = ET.SubElement(clubs_elem, "CLUB", {
                'name': unquote(team.name),
                'code': team.code,
                'nation': team.nation,
                'type': team.type
            })
            
            # Add athletes
            if club_code in athletes_by_club:
                self._add_athletes(
                    club_elem, 
                    athletes_by_club[club_code],
                    competition
                )
            
            # Add relays
            if club_code in relays_by_club:
                self._add_relays(
                    club_elem,
                    relays_by_club[club_code],
                    competition
                )
    
    def _add_athletes(
        self, 
        club_elem: ET.Element, 
        athletes: list,
        competition: Competition
    ) -> None:
        """Add athletes to club."""
        athletes_elem = ET.SubElement(club_elem, "ATHLETES")
        
        for athlete in athletes:
            athlete_elem = ET.SubElement(athletes_elem, "ATHLETE", {
                'athleteid': athlete.athlete_id,
                'lastname': unquote(athlete.lastname),
                'firstname': unquote(athlete.firstname),
                'gender': athlete.gender.value,
                'birthdate': athlete.birthdate.strftime("%Y-%m-%d")
            })
            
            # Add entries
            if athlete.athlete_id in competition.athlete_entries:
                entries = competition.athlete_entries[athlete.athlete_id]
                self._add_entries(athlete_elem, entries)
            
            # Add results
            if athlete.athlete_id in competition.athlete_results:
                results = competition.athlete_results[athlete.athlete_id]
                self._add_results(athlete_elem, results)
    
    def _add_entries(self, athlete_elem: ET.Element, entries: list) -> None:
        """Add entries for an athlete."""
        entries_elem = ET.SubElement(athlete_elem, "ENTRIES")
        
        for entry in entries:
            entry_attrs = {
                'entrytime': entry.entry_time,
                'eventid': entry.event_id
            }
            
            if entry.heat:
                entry_attrs['heat'] = entry.heat
            if entry.lane:
                entry_attrs['lane'] = entry.lane
            
            entry_elem = ET.SubElement(entries_elem, "ENTRY", entry_attrs)
            
            if entry.meet_info:
                ET.SubElement(
                    entry_elem, 
                    "MEETINFO", 
                    {'date': entry.meet_info.strftime("%Y-%m-%d")}
                )
    
    def _add_results(self, athlete_elem: ET.Element, results: list) -> None:
        """Add results for an athlete."""
        results_elem = ET.SubElement(athlete_elem, "RESULTS")
        
        for result in results:
            result_attrs = {
                'eventid': result.event_id,
                'resultid': result.result_id,
                'place': result.place,
                'lane': result.lane,
                'heat': result.heat,
                'heatid': result.heat_id,
                'swimtime': result.swimtime
            }
            
            if result.points:
                result_attrs['points'] = result.points
            if result.reaction_time:
                result_attrs['reactiontime'] = result.reaction_time
            
            result_elem = ET.SubElement(results_elem, "RESULT", result_attrs)
            
            # Add splits
            if result.splits:
                splits_elem = ET.SubElement(result_elem, "SPLITS")
                for split in result.splits:
                    ET.SubElement(splits_elem, "SPLIT", {
                        'distance': str(split.distance),
                        'swimtime': split.swimtime
                    })
    
    def _add_relays(
        self,
        club_elem: ET.Element,
        relays: list,
        competition: Competition
    ) -> None:
        """Add relays to club."""
        relays_elem = ET.SubElement(club_elem, "RELAYS")
        
        for relay in relays:
            relay_elem = ET.SubElement(relays_elem, "RELAY", {
                'number': str(relay.number),
                'agemax': str(relay.agemax),
                'agemin': str(relay.agemin),
                'agetotalmax': '-1',
                'gender': relay.gender.value,
                'name': relay.team.name
            })
            
            # Add results for this relay
            team_code = relay.team.code
            if team_code in competition.relay_results:
                results_elem = ET.SubElement(relay_elem, "RESULTS")
                
                for result in competition.relay_results[team_code]:
                    result_attrs = {
                        'eventid': result.event_id,
                        'resultid': result.result_id,
                        'place': result.place,
                        'lane': result.lane,
                        'heat': result.heat,
                        'heatid': result.heat_id,
                        'swimtime': result.swimtime,
                        'reactiontime': result.reaction_time
                    }
                    
                    result_elem = ET.SubElement(results_elem, "RESULT", result_attrs)
                    
                    # Add splits
                    if result.splits:
                        splits_elem = ET.SubElement(result_elem, "SPLITS")
                        for split in result.splits:
                            ET.SubElement(splits_elem, "SPLIT", {
                                'distance': str(split.distance),
                                'swimtime': split.swimtime
                            })
                    
                    # Add relay positions
                    positions_elem = ET.SubElement(result_elem, "RELAYPOSITIONS")
                    for position in relay.positions:
                        ET.SubElement(positions_elem, "RELAYPOSITION", {
                            'number': str(position.number),
                            'athleteid': position.athlete.athlete_id,
                            'reactiontime': position.reaction_time
                        })
    
    def _format_xml(self) -> str:
        """Format XML with proper indentation and encoding."""
        xml_string = ET.tostring(self.root, encoding='unicode')
        dom = xml.dom.minidom.parseString(xml_string)
        
        # Pretty print with UTF-8 encoding
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Add proper encoding declaration
        lines = pretty_xml.split('\n')
        lines[0] = '<?xml version="1.0" encoding="utf-8" standalone="no"?>'
        
        return '\n'.join(lines)
    
    def save(
        self, 
        data: str, 
        filename: str, 
        output_dir: str = "processed_data"
    ) -> None:
        """
        Save encoded XML to file.
        
        Args:
            data: XML string
            filename: Output filename (without extension)
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / f"{filename}.lef"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        
        print(f"LENEX file saved: {file_path}")