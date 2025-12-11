import os
import json
import pathlib
import datetime
import requests
import utils  # Assumes you have a 'utils.py' with all your helper functions

from .data_source import IMeetDataSource
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
# Import any other models you have (e.g., Split, Constructor)


class ScrapedDataAdapter(IMeetDataSource):
    """
    Adapter to convert the scraped JSON data from local files
    into a Lenex Meet object.
    """

    def __init__(self, scraped_data_path: str, pool_length: int):
        self.data_path = scraped_data_path
        self.pool_length = pool_length
        # Get competition infos once, as it's used in both methods
        self.competition_infos = utils.get_competition_infos(self.data_path)
        print(f"Adapter initialized. Data path: '{self.data_path}'")

    def get_meet_object(self) -> Meet:
        """
        Main adapter method. Runs the conversion and maps
        the resulting dictionary to the OOP model.
        """
        # Step 1: Run your original function to get the intermediate dict
        print("Adapter: Building intermediate dictionary from JSON files...")
        data = self._build_intermediate_dict()
        print("Adapter: Intermediate dictionary built.")

        # Step 2: Map the dict to our data classes
        print("Adapter: Mapping dictionary to OOP model...")
        meet_object = self._map_dict_to_model(data)
        print("Adapter: OOP model mapping complete.")
        
        return meet_object

    def _map_dict_to_model(self, data: dict) -> Meet:
        """
        Walks the intermediate dictionary and builds the
        OOP data class objects.
        """
        
        # --- Build Clubs and Athletes ---
        final_clubs = []
        for c_name, c_data in data['clubs'].items():
            club_infos = c_data['infos']
            
            final_athletes = []
            if 'athletes' in c_data:
                for a_id, a_data in c_data['athletes'].items():
                    ath_infos = a_data['athlete_infos']
                    
                    # Build Results for athlete
                    final_results = []
                    if 'results' in a_data:
                        for r_dict in a_data['results']:
                            # Here, you would also build a list of Split objects
                            # final_splits = [Split(**s) for s in r_dict['splits']]
                            final_results.append(Result(
                                resultid=r_dict['resultid'],
                                eventid=r_dict['eventid'],
                                swimtime=r_dict['swimtime'],
                                place=r_dict.get('place'),
                                lane=r_dict.get('lane'),
                                heatid=r_dict.get('heatid'),
                                points=r_dict.get('points'),
                                reactiontime=r_dict.get('reactiontime')
                                # splits=final_splits
                            ))
                    
                    # Build Athlete
                    final_athletes.append(Athlete(
                        athleteid=ath_infos['athleteid'],
                        lastname=requests.utils.unquote(ath_infos['lastname']),
                        firstname=requests.utils.unquote(ath_infos['firstname']),
                        gender=ath_infos['gender'],
                        birthdate=f"{ath_infos['birthdate']}-01-01",
                        results=final_results
                        # You would also map 'entries' here
                    ))
            
            # ... Build Relays ...
            # final_relays = [] ...

            # Build Club
            final_clubs.append(Club(
                name=requests.utils.unquote(club_infos['name']),
                code=utils.get_team_code(club_infos['name']),
                nation=club_infos['nation'],
                athletes=final_athletes
                # relays=final_relays
            ))

        # --- Build Sessions and Events ---
        final_sessions = []
        for s_num, s_data in data['sessions'].items():
            
            final_events = []
            for e_dict in s_data['events']:
                
                # Build Rankings
                final_rankings = []
                for r_dict in e_dict['agegroup']['results']:
                    final_rankings.append(Ranking(
                        place=int(r_dict['place']),
                        resultid=r_dict['resultid']
                        # order=r_dict.get('order')
                    ))
                
                # Build AgeGroup
                ag_dict = e_dict['agegroup']
                agegroup = AgeGroup(
                    agegroupid=ag_dict['id'],
                    agemax=ag_dict['age_costraints']['agemax'],
                    agemin=ag_dict['age_costraints']['agemin'],
                    rankings=final_rankings
                )

                # Build Heats
                final_heats = []
                for h_id, h_dict in e_dict['heats'].items():
                    final_heats.append(Heat(
                        heatid=h_dict['heatid'],
                        number=h_dict['number'],
                        daytime=h_dict['daytime']
                    ))

                # Build Swimstyle
                ss_dict = e_dict['lenex']['swimstyle']
                swimstyle = Swimstyle(
                    distance=ss_dict['distance'],
                    relaycount=ss_dict['relaycount'],
                    stroke=ss_dict['stroke']
                )

                # Build Event
                evt_dict = e_dict['lenex']['event']
                final_events.append(Event(
                    eventid=evt_dict['eventid'],
                    number=int(evt_dict['number']),
                    preveventid=evt_dict['preveventid'],
                    gender=evt_dict['gender'],
                    round=evt_dict['round'],
                    daytime=evt_dict['daytime'],
                    swimstyle=swimstyle,
                    agegroups=[agegroup], # Wrap in list
                    heats=final_heats
                ))

            # Build Session
            final_sessions.append(Session(
                number=int(s_data['infos']['number']),
                date=s_data['infos']['date'],
                daytime=s_data['infos']['daytime'],
                events=final_events
            ))

        # --- Build Meet ---
        evt_data = data['competition_infos']['event']
        final_meet = Meet(
            name=evt_data['name'],
            city=evt_data['city'],
            nation=evt_data['nation'],
            course=evt_data['course'],
            timing=evt_data['timing'],
            sessions=final_sessions,
            clubs=final_clubs
            # You would also map POOL, POINTTABLE, and CONSTRUCTOR
            # info from data['competition_infos'] here
        )
        
        return final_meet


    def _build_intermediate_dict(self) -> dict:
        """
        This is your original 'convert_to_lenex' function.
        It reads scraped files and builds a large dictionary.
        """
        
        eventid = 1
        events: list = []
        prelims_eventid: list = []
        sessions: dict[str, list] = {}
        entries: dict[str, list] = {  # Fixed dict key type
            'athletes': [],
            'relays': []
        }

        # Create directory to store the processed data
        # This is not needed if you just read from 'scraped_data'
        # pathlib.Path('processed_data').mkdir(parents=True, exist_ok=True)
        
        schedule_path = os.path.join(self.data_path, 'schedules', 'by_date')
        if not os.path.exists(schedule_path):
            print(f"Error: Schedule path not found: {schedule_path}")
            return {}

        for session_n in range(len(os.listdir(schedule_path)) + 1):
            filename = f'ScheduleByDate_{session_n + 1}.JSON'
            filepath = os.path.join(schedule_path, filename)
            
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data: list = json.loads(f.read())['e']
                    session = []
                    for event in data:
                        # Assumes helper functions are in 'utils.py'
                        heats_data = utils.get_heats(event, eventid, self.pool_length, self.data_path)
                        infos = utils.get_event_infos(event, eventid, filename, eventid) | { 
                            'agegroup': heats_data['agegroup']}
                        race = infos | {'heats': heats_data['heats']}
                        
                        if heats_data['entries']['type'] == 'heats':
                            entries['athletes'] += heats_data['entries']['data'][0]
                        else:
                            for athlete in heats_data['entries']['data'][0]:
                                entries['athletes'] += athlete
                            entries['relays'] += heats_data['entries']['data'][1]
                        
                        if race['lenex']['event']['preveventid'] == '-1':
                            prelims_eventid.append({
                                'race_code': utils.RACE_CODES[event["d_en"]],
                                'eventid': race['lenex']['event']['eventid'],
                                'category': event['c0']
                            })

                        eventid = eventid + 1
                        
                        if race['lenex']['event']['preveventid'] == '00':
                            for prelim in prelims_eventid:
                                if event['c2'] == '006' :
                                    if race['race_code'] == prelim['race_code'] and race['category'] == prelim['category']:
                                        race['lenex']['event']['preveventid'] = prelim['eventid']
                                else:
                                    if race['race_code'] == prelim['race_code'] and race['category'] == prelim['category']:
                                        race['lenex']['event']['preveventid'] = prelim['eventid']
                        
                        events.append(race)
                        session.append(race)
                    sessions[str(session_n + 1)] = session

        results_path = os.path.join(self.data_path, 'results')
        for key in sessions.keys():
            if not sessions[key]: # Skip empty sessions
                continue 
            
            results_filename = sessions[key][0]["jsonfilename"]
            results_filepath = os.path.join(results_path, results_filename)
            
            with open(results_filepath, 'r', encoding='utf-8') as f:
                data = json.loads(f.read())['Heat']
                sessions[key] = {
                    'infos': {
                        'number': str(key),
                        'date': datetime.datetime.strptime(data['UffDate'], "%d/%m/%Y").strftime("%Y-%m-%d"),
                        'daytime': data['UffTime']
                    },
                    'events': sessions[key]
                }

        clubs = {}
        for entry in entries['athletes']:
            infos = entry['athlete_infos']
            club_name = infos['team']['name']
            athleteid = infos['athleteid']
            if club_name not in clubs.keys():
                club_infos = infos['team']
                del infos['team']
                clubs[club_name] = {
                    'infos': club_infos,
                    'athletes': {
                        athleteid: {'athlete_infos': infos}
                    },
                    'relays': []
                }
                if len(entry.keys()) > 1:
                    clubs[club_name]['athletes'][athleteid]['entries'] = [
                        entry['entry']]
                    clubs[club_name]['athletes'][athleteid]['results'] = [
                        entry['result']]

            elif athleteid not in clubs[club_name]['athletes'].keys():
                del infos['team']
                clubs[club_name]['athletes'][athleteid] = {'athlete_infos': infos}
                if len(entry.keys()) > 1:
                    clubs[club_name]['athletes'][athleteid]['entries'] = [
                        entry['entry']]
                    clubs[club_name]['athletes'][athleteid]['results'] = [
                        entry['result']]
            else:
                try:
                    if len(entry.keys()) > 1:
                        clubs[club_name]['athletes'][athleteid]['entries'].append(
                            entry['entry'])
                        clubs[club_name]['athletes'][athleteid]['results'].append(
                            entry['result'])
                except KeyError:
                    clubs[club_name]['athletes'][athleteid]['entries'] = [
                        entry['entry']]
                    clubs[club_name]['athletes'][athleteid]['results'] = [
                        entry['result']]

        for entry in entries['relays']:
            club_name = entry['relay_infos']['team']['name']
            athleteid = entry['relay_infos']['athleteid'] # Fixed: athleteid was not defined

            if club_name not in clubs.keys():
                clubs[club_name] = {
                    'infos': entry['relay_infos']['team'],
                    'athletes': {},
                    'relays': [entry]
                }
                for athlete in entry['result']['splits']['player_positions']:
                    # Use the correct athleteid from the loop
                    ath_id = athlete['athleteid'] 
                    if ath_id not in clubs[club_name]['athletes']:
                        clubs[club_name]['athletes'][ath_id] = {
                            'athlete_infos': athlete
                        }
            else:
                clubs[club_name]['relays'].append(entry)
                # Also add relay athletes if they aren't in the club list
                for athlete in entry['result']['splits']['player_positions']:
                    ath_id = athlete['athleteid']
                    if ath_id not in clubs[club_name]['athletes']:
                         clubs[club_name]['athletes'][ath_id] = {
                            'athlete_infos': athlete
                        }

        # Return everything needed for the mapping function
        return {
            'sessions': sessions, 
            'clubs': clubs,
            'competition_infos': self.competition_infos
        }