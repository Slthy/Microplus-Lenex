import requests
import json
import pathlib
import os
import datetime
import utils
#TODO: #1 setup python env, (do in at the end)

def scrape_data(url: str) -> None:
    url_elab: list = utils.url(url)
    base_url = url_elab[0]
    event = url_elab[1]
    counter_generale = requests.get(
        f'{base_url}{event}/NU/CounterGenerale.json?').text[:-2]
    contatori = requests.get(
        f'{base_url}{event}/NU/Contatori.json?x={counter_generale}').json()['contatori']

    for obj in contatori:
        # download json
        scraped_data = requests.get(
            f'{base_url}{event}/NU/{obj["nomefile"]}?x={obj["counter"]}').json()

        # assigns a category to the downloaded json. This category will also be part of its filepath
        file_type = obj['cod'] if obj['cod'] in utils.FILE_TYPES.keys(
        ) else 'other'

        # create directory for a new type of file
        pathlib.Path(
            f'scraped_data/{utils.FILE_TYPES[file_type]}').mkdir(parents=True, exist_ok=True)

        # write file into category path
        with open(f'scraped_data/{utils.FILE_TYPES[file_type]}/{scraped_data["jsonfilename"]}', 'w') as f:
            f.write(json.dumps(scraped_data))
            f.close()


def get_competition_infos() -> dict:

    # reads the first 'result' in the 'results' folder, retrieves generic data and asks to the user the missing infos
    with open(f"scraped_data/results/{os.listdir('scraped_data/results')[0]}", 'r') as f:
        data = json.loads(f.read())
        pool_length_code = input('insert course lenght (LCM or SCM): ')
        return {
            'data': {  # this script is specifically designed to scrape data from Microplus' systems #TODO: maybe put these infos directly in the xml
                'constructor': {
                    'name': 'Microplus Informatica Srl',
                    'zip': 'IT-12030',
                    'city': 'Marene',
                    'email': 'mbox@microplus.it',
                    'internet': 'https://www.microplus.it'
                },
                'event': {  # generic data about the competition's venue
                    'name': data['Export']['ExpName'],
                    'desciption': data['Export']['ExpDescr'],
                    'city': data['Event']['Place'].split(',')[0],
                    'nation': 'ITA' if data['Event']['Place'].split(',')[0] == 'Roma'
                    else input(f'insert nation (city: {data["Event"]["Place"].split(",")[0]}): '),
                    'course': pool_length_code,  # TODO: #2 check?, inquirer module
                    'timing': "AUTOMATIC",
                    'pool_lane_min': '0',
                    'pool_lane_max': '9'
                },
            },
            'pool_length': 50 if pool_length_code == 'LCM' else 25
        }


def get_entry_time(category: str, race_code, event_type: str, PlaCod: str) -> str: # returns the entry time in an event for a given athlete
    with open(f'scraped_data/startlists/NU{category}{utils.utils.RACE_CODES[race_code]}STAR{event_type} 001.JSON', 'r') as f:
        for entry in json.loads(f.read())['data']:
            if entry['PlaCod'] == PlaCod:
                return utils.format_time(entry['MemIscr'])


def get_heats(event: dict, eventid: int, pool_length: int) -> dict: # returns LENEX 'heats' component for the given event and all the athlete entries 
    with open(f'scraped_data/results/NU{event["c0"]}{utils.RACE_CODES[event["d_en"]]}CLAS{event["c2"][::2]} 001.JSON', 'r') as f:
        heat_entries: list = json.loads(f.read())
        date = heat_entries['Heat']['UffDate']
        data: list = heat_entries['data']
        athlete_entries = []
        heats = {}
        heat_n = 1
        for entry in data:
            entrytime = get_entry_time(
                event["c0"], event["d_en"], event["c2"][::2], entry['PlaCod'])
            heatid = f'{heat_n}{"0"*(5-(len(str(heat_n)) + len(str(eventid))))}{eventid}' # 'heatid' is composed of the heat's at the head, eventid at the tail, filled in between by '0's
            swimtime = utils.format_time(entry['MemPrest'])
            splits = []
            for index, time in enumerate(entry['MemFields'][1:]): #first element is blank every time, so we cut it
                if time['V'] == "":
                    break

                splits.append({
                    'distance': str(pool_length*index + pool_length),
                    'swimtime': utils.format_time(time['V'])
                })

            athlete_entries.append({
                'athlete_infos': {
                    # TODO: #5 swimrankings codes if possible (and needed)
                    'athleteid': entry['PlaCod'],
                    'lastname': entry['PlaSurname'],
                    'firstname': entry['PlaName'],
                    'gender': event["c0"][-1],
                    'birthdate': entry['PlaBirth'],
                    'team': {
                        'name': entry['TeamDescrIta'],
                        'shortname': entry['TeamDescrItaVis'],
                        'code': entry['PlaNat'],
                        'nation': entry['PlaNat'],
                        'type': 'CLUB'  # hardcoded
                    }
                },
                'entry': {
                    'eventid': eventid,
                    'entrytime': entrytime,
                    'heat': entry['b'],
                    'lane': entry['PlaLane'],
                    'meetinfo': date
                },
                'result': {
                    'eventid': eventid,
                    'place': entry['PlaCls'],
                    'lane': entry['PlaLane'],
                    'heat': heat_n,
                    'heatid': heatid,
                    'swimtime': swimtime,
                    'reactiontime': '',  # TODO: #6 check if value is given in other microplus events
                    'splits': splits
                }
            })
            if entry['b'] not in heats.keys():
                heats[entry['b']] = [{
                    # TODO: #7 check for possible bug regarding this field, sometimes is empty
                    'daytime': event['h'],
                    # heatid is by default 5 char long, composed by the heat's number at the start and event's id at the end, in the middle '0's fill the remaining chars
                    'heatid': heatid,
                    'number': str(heat_n)
                }]
                heat_n = heat_n + 1
        f.close()
    return {'heats': dict(sorted(heats.items())), 'entries': athlete_entries}


def get_event_infos(event: dict, eventid: int, filename: str) -> dict:
    swimstyle_split = event["d_en"].split('m')
    return {
        'session': int(filename[15:-5:]),
        'name': event["d_en"],
        'category': event['c0'],
        'race_code': utils.RACE_CODES[event["d_en"]],
        'race_type': event['c2'],
        # results filename
        'jsonfilename': f'NU{event["c0"]}{utils.RACE_CODES[event["d_en"]]}CLAS{event["c2"][-2::]} 001.JSON',
        'lenex': {
            'event': {
                'eventid': str(eventid),
                'number': utils.RACE_CODES[event["d_en"]],
                # '-1' means that the event is a preliminary or heat, so there isn't "parent" event for the current event.
                'preveventid': '-1' if (event['c2'] == '001' or event['c2'] == '007') else '00',
                'gender': event['c0'][-1::],
                'round': utils.RACE_TYPES[event["c2"]]['lenex'],
                'daytime': event['h'],
                'pool': {
                    'lanemax': '8' if utils.RACE_TYPES[event["c2"]]['microplus'] == '007' or '006' else '9',
                    'lanemin': '1' if utils.RACE_TYPES[event["c2"]]['microplus'] == '007' or '006' else '0'
                }
            },
            'swimstyle': {
                'distance': swimstyle_split[0].strip() if 'x' not in swimstyle_split[0] else swimstyle_split[0].strip().replace('4 x ', ''),
                'relaycount': '4' if 'x' in swimstyle_split[0].strip() else '1',
                'stroke':  utils.LENEX_STROKES[swimstyle_split[1].strip()]
            }
        }
    }


def convert_to_lenex(pool_length: int) -> dict:

    events = []
    prelims_eventid = []
    eventid = 1
    athletes_entries = []

    # create directory to store the processed data
    pathlib.Path('processed_data').mkdir(parents=True, exist_ok=True)
    for filename in os.listdir('scraped_data/schedules/by_date'):
        file = os.path.join('scraped_data/schedules/by_date', filename)

        if os.path.isfile(file):
            with open(file, 'r') as f:
                data: list = json.loads(f.read())['e']
                for event in data:
                    infos = get_event_infos(event, eventid, filename)
                    heats_data = get_heats(event, eventid, pool_length)
                    race = infos | heats_data['heats']
                    athletes_entries = athletes_entries + heats_data['entries']
                    # if the event is a preliminary or heat, put race_code, eventid and -current event's- category into the prelims list
                    if race['lenex']['event']['preveventid'] == '-1':
                        prelims_eventid.append({
                            'race_code': utils.RACE_CODES[event["d_en"]],
                            'eventid': race['lenex']['event']['eventid'],
                            'category': event['c0']
                        })
                    eventid = eventid + 1
                    events.append(race)
                f.close()

    for race in events:
        # if event has a prev_event, the parent event in the prelims list. This script is designed for 'normal' event, no semis. # TODO: #8 handle semis (and quarters)
        if race['lenex']['event']['preveventid'] == '00':
            for prelim in prelims_eventid:
                if prelim['race_code'] == race['race_code'] and prelim['category'] == race['category']:
                    race['lenex']['event']['preveventid'] = prelim['eventid']

    sessions = {}
    for event in events:  # append event to the corresponding key, which is the session's number
        if event['session'] in sessions.keys():
            sessions[event['session']].append(event)
        else:
            sessions[event['session']] = [event]
    sessions = dict(sorted(sessions.items()))

    for key in sessions.keys():  # add contextual data for the session
        with open(f'scraped_data/results/{sessions[key][0]["jsonfilename"]}', 'r') as f:
            data = json.loads(f.read())['Heat']
            sessions[key] = {
                'infos': {
                    'number': str(key),
                    'date': datetime.datetime.strptime(data['UffDate'], "%d/%m/%Y").strftime("%Y-%m-%d"),
                    'daytime': data['UffTime']
                },
                'events': sessions[key]
            }
            f.close()

    clubs = {}
    for entry in athletes_entries:
        club_name = entry['athlete_infos']['team']['name']
        athleteid = entry['athlete_infos']['athleteid']

        if club_name not in clubs.keys(): # new club 
            club_infos = entry['athlete_infos']['team']
            del entry['athlete_infos']['team']

            clubs[club_name] = {
                'infos': club_infos,
                'athletes': {
                    athleteid: {
                        'athlete_infos': entry['athlete_infos'],
                        'entries': [entry['entry']],
                        'results': [entry['result']]
                    }
                }
            }
        elif athleteid not in clubs[club_name]['athletes'].keys(): # club already in 'clubs' dict, new athlete to add
            del entry['athlete_infos']['team']

            clubs[club_name]['athletes'][athleteid] = {
                'athlete_infos': entry['athlete_infos'],
                'entries': [entry['entry']],
                'results': [entry['result']]
            }
        else: # both club and athlete are in the respective dicts, append new data to 'entries' and 'results' field
            clubs[club_name]['athletes'][athleteid]['entries'].append(
                entry['entry'])
            clubs[club_name]['athletes'][athleteid]['results'].append(
                entry['result'])

    return {'sessions': sessions, 'clubs': clubs}


def build_lenex() -> None:
    competition_infos: dict = get_competition_infos()
    converted_data = convert_to_lenex(competition_infos['pool_length'])
    with open('processed_data/lenex_data.json', 'w') as f:  # write results
        f.write(json.dumps(competition_infos['data'] | converted_data))
        f.close()