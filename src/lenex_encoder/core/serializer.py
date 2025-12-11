from lxml import etree
from ..model.meet import Meet
from ..model.session import Session
from ..model.event import Event
from ..model.club import Club
from ..model.athlete import Athlete
from ..model.result import Result
from ..model.ranking import Ranking
from ..model.agegroup import AgeGroup
from ..model.heat import Heat
from ..model.swimstyle import Swimstyle
# Import other models as you add them (Split, Entry, Relay, etc.)

class LenexSerializer:
    """
    Handles converting the Python data class model to a Lenex 3.0
    XML string.
    
    It receives a fully populated 'Meet' object and builds the
    XML tree from it.
    """

    def __init__(self, meet: Meet):
        """
        Initializes the serializer with the meet object to be processed.
        
        Args:
            meet (Meet): The populated Meet data class object.
        """
        self.meet = meet

    def _clean_attrs(self, data_dict: dict) -> dict:
        """
        Private helper to clean an attributes dictionary.
        - Removes keys where the value is None.
        - Converts all remaining values to strings (as lxml requires).
        """
        return {k: str(v) for k, v in data_dict.items() if v is not None}

    def to_xml_string(self) -> str:
        """
        Generates the final, formatted Lenex XML string.
        """
        # Create the root <LENEX> element
        root = etree.Element("LENEX", version="3.0")

        # --- MEETS ---
        meets_el = etree.Element("MEETS")
        
        # --- MEET ---
        meet_attrs = self._clean_attrs({
            'name': self.meet.name,
            'city': self.meet.city,
            'nation': self.meet.nation,
            'course': self.meet.course,
            'timing': self.meet.timing
        })
        meet_el = etree.SubElement(meets_el, "MEET", **meet_attrs)

        # --- POOL & POINTTABLE ---
        # self._build_pool(meet_el)
        # self._build_pointtable(meet_el)

        # --- Build all child branches ---
        self._build_sessions(meet_el, self.meet.sessions)
        self._build_clubs(meet_el, self.meet.clubs)
        
        root.append(meets_el)

        # --- Serialize to String ---
        xml_string = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding='utf-8',
            standalone="no"
        ).decode('utf-8')

        return xml_string

    def _build_sessions(self, parent_el, sessions: list[Session]):
        """Builds the <SESSIONS> collection."""
        if not sessions:
            return
            
        sessions_el = etree.SubElement(parent_el, "SESSIONS")
        for session in sessions:
            session_attrs = self._clean_attrs({
                'number': session.number,
                'date': session.date,
                'daytime': session.daytime,
                'name': session.name
            })
            session_el = etree.SubElement(sessions_el, "SESSION", **session_attrs)
            self._build_events(session_el, session.events)

    def _build_events(self, parent_el, events: list[Event]):
        """Builds the <EVENTS> collection for a session."""
        if not events:
            return
            
        events_el = etree.SubElement(parent_el, "EVENTS")
        for event in events:
            event_attrs = self._clean_attrs({
                'number': event.number,
                'eventid': event.eventid,
                'gender': event.gender,
                'round': event.round,
                'preveventid': event.preveventid,
                'daytime': event.daytime
            })
            event_el = etree.SubElement(events_el, "EVENT", **event_attrs)
            
            # Build <SWIMSTYLE>
            self._build_swimstyle(event_el, event.swimstyle)
            # Build <AGEGROUPS>
            self._build_agegroups(event_el, event.agegroups)
            # Build <HEATS>
            self._build_heats(event_el, event.heats)

    def _build_swimstyle(self, parent_el, swimstyle: Swimstyle):
        """Builds the <SWIMSTYLE> element for an event."""
        if not swimstyle:
            return
            
        ss_attrs = self._clean_attrs({
            'distance': swimstyle.distance,
            'relaycount': swimstyle.relaycount,
            'stroke': swimstyle.stroke,
            'technique': swimstyle.technique
        })
        etree.SubElement(parent_el, "SWIMSTYLE", **ss_attrs)

    def _build_agegroups(self, parent_el, agegroups: list[AgeGroup]):
        """Builds the <AGEGROUPS> collection for an event."""
        if not agegroups:
            return
            
        agegroups_el = etree.SubElement(parent_el, "AGEGROUPS")
        for ag in agegroups:
            ag_attrs = self._clean_attrs({
                'agegroupid': ag.agegroupid,
                'agemin': ag.agemin,
                'agemax': ag.agemax,
                'gender': ag.gender
            })
            ag_el = etree.SubElement(agegroups_el, "AGEGROUP", **ag_attrs)
            self._build_rankings(ag_el, ag.rankings)

    def _build_rankings(self, parent_el, rankings: list[Ranking]):
        """Builds the <RANKINGS> collection for an age group."""
        if not rankings:
            return
            
        rankings_el = etree.SubElement(parent_el, "RANKINGS")
        for r in rankings:
            r_attrs = self._clean_attrs({
                # 'order': r.order, # Add 'order' to your Ranking model
                'place': r.place,
                'resultid': r.resultid
            })
            etree.SubElement(rankings_el, "RANKING", **r_attrs)

    def _build_heats(self, parent_el, heats: list[Heat]):
        """Builds the <HEATS> collection for an event."""
        if not heats:
            return
            
        heats_el = etree.SubElement(parent_el, "HEATS")
        for h in heats:
            h_attrs = self._clean_attrs({
                'heatid': h.heatid,
                'number': h.number,
                'daytime': h.daytime,
                'final': h.final,
                'status': h.status
            })
            etree.SubElement(heats_el, "HEAT", **h_attrs)

    def _build_clubs(self, parent_el, clubs: list[Club]):
        """Builds the <CLUBS> collection for the meet."""
        if not clubs:
            return
            
        clubs_el = etree.SubElement(parent_el, "CLUBS")
        for club in clubs:
            club_attrs = self._clean_attrs({
                'name': club.name,
                'code': club.code,
                'nation': club.nation,
                # 'type': club.type # Add 'type' to your Club model
            })
            club_el = etree.SubElement(clubs_el, "CLUB", **club_attrs)
            
            self._build_athletes(club_el, club.athletes)
            # self._build_relays(club_el, club.relays) # Future
            
    def _build_athletes(self, parent_el, athletes: list[Athlete]):
        """Builds the <ATHLETES> collection for a club."""
        if not athletes:
            return
            
        athletes_el = etree.SubElement(parent_el, "ATHLETES")
        for athlete in athletes:
            ath_attrs = self._clean_attrs({
                'athleteid': athlete.athleteid,
                'lastname': athlete.lastname,
                'firstname': athlete.firstname,
                'gender': athlete.gender,
                'birthdate': athlete.birthdate
            })
            athlete_el = etree.SubElement(athletes_el, "ATHLETE", **ath_attrs)
            
            # self._build_entries(athlete_el, athlete.entries) # Future
            self._build_results(athlete_el, athlete.results)

    def _build_results(self, parent_el, results: list[Result]):
        """Builds the <RESULTS> collection for an athlete."""
        if not results:
            return
            
        results_el = etree.SubElement(parent_el, "RESULTS")
        for res in results:
            res_attrs = self._clean_attrs({
                'eventid': res.eventid,
                'resultid': res.resultid,
                'place': res.place,
                'lane': res.lane,
                'heatid': res.heatid,
                'swimtime': res.swimtime,
                'points': res.points,
                'reactiontime': res.reactiontime,
                'status': res.status
            })
            result_el = etree.SubElement(results_el, "RESULT", **res_attrs)
            
            # self._build_splits(result_el, res.splits) # Future