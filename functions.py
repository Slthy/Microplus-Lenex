import requests
import json
import pathlib
import os
import datetime

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
    "001": {
        'microplus': 'preliminary',
        'lenex': 'PRE'
    },
    "002": {
        'microplus': 'spareggio',
        'lenex': 'SOP'
    },
    "003": {
        'microplus': 'semifinals',
        'lenex': 'SEM'
    },
    "004": {
        'microplus': 'spareggio2',
        'lenex': 'SOS'
    },
    "005": {
        'microplus': 'final',
        'lenex': 'FIN'
    },
    "006": {
        'microplus': 'young final',
        'lenex': 'FIN'
    },
    "007": {
        'microplus': 'heats',
        'lenex': 'TIM'
    }
}

FILE_TYPES = {
    'SCH_D': 'schedules/by_date',
    'SCH_E': 'schedules/by_event',
    'STL1': 'startlists',
    'SUM':  'summary',
    'CGR1': 'results',
    'other': 'other'
}

LENEX_STROKES = {
    'Freestyle': 'FREE',
    'Butterfly': 'FLY',
    'Breaststroke': 'BREAST',
    'Backstroke': 'BACK',
    'Individual Medley': 'MEDLEY',
    'Medley': 'MEDLEY'
}


def url_util(url: str) -> list:
    output = url.split('NU_')
    return [output[0]+'export/NU_', output[1].replace('_web.php', '')]


def scrape_data(url: str):
    url_elab: list = url_util(url)
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
        file_type = obj['cod'] if obj['cod'] in FILE_TYPES.keys() else 'other'

        # create directory for a new type of file
        pathlib.Path(
            f'scraped_data/{FILE_TYPES[file_type]}').mkdir(parents=True, exist_ok=True)

        # write file into category path
        with open(f'scraped_data/{FILE_TYPES[file_type]}/{scraped_data["jsonfilename"]}', 'w') as f:
            f.write(json.dumps(scraped_data))
            f.close()


def get_competition_infos() -> dict:

    # reads the first 'result' in the 'results' folder, retrieves generic data and asks to the user the missing infos
    with open(os.listdir('scraped_data/results')[0], 'r') as f:
        data = json.loads(f.read())
        return {  # this script is specifically designed to scrape data from Microplus' systems #TODO: maybe put these infos directly in the xml
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
                'course': input('insert course lenght (LCM or SCM): '),
                'timing': "AUTOMATIC",
                'pool_lane_min': '0',
                'pool_lane_max': '10'
            }
        }


def get_heats(event: dict, eventid: int) -> dict:
    with open(f'scraped_data/results/NU{event["c0"]}{RACE_CODES[event["d_en"]]}CLAS{event["c2"][-2::]} 001.JSON', 'r') as f:
        heat_entries: list = json.loads(f.read())['data']
        heats = {}
        heat_n = 1
        for entry in heat_entries:
            if entry['b'] not in heats.keys():
                heats[entry['b']] = [{
                    'daytime': event['h'],
                    'heatid': f'{heat_n}{"0"*(5-(len(str(heat_n)) + len(str(eventid))))}{eventid}', # heatid is by default 5 char long, composed by the heat's number at the start and event's id at the end, in the middle '0's fill the remaining chars
                    'number': str(heat_n)
                }]
                heat_n = heat_n + 1
        f.close()
    return {'heats': dict(sorted(heats.items()))}


def get_event_infos(event: dict, eventid: int, filename: str) -> dict:
    swimstyle_split = event["d_en"].split('m')
    return {
        'session': int(filename[15:-5:]),
        'name': event["d_en"],
        'category': event['c0'],
        'race_code': RACE_CODES[event["d_en"]],
        'race_type': event['c2'],
        # results filename
        'jsonfilename': f'NU{event["c0"]}{RACE_CODES[event["d_en"]]}CLAS{event["c2"][-2::]} 001.JSON',
        'lenex': {
            'event': {
                'eventid': str(eventid),
                'number': RACE_CODES[event["d_en"]],
                # '-1' means that the event is a preliminary or heat, so there isn't "parent" event for the current event.
                'preveventid': '-1' if (event['c2'] == '001' or event['c2'] == '007') else '00',
                'gender': event['c0'][-1::],
                'round': RACE_TYPES[event["c2"]]['lenex'],
                'daytime': event['h']
            },
            'swimstyle': {
                'distance': swimstyle_split[0].strip() if 'x' not in swimstyle_split[0] else swimstyle_split[0].strip().replace('4 x ', ''),
                'relaycount': '4' if 'x' in swimstyle_split[0].strip() else '1',
                'stroke':  LENEX_STROKES[swimstyle_split[1].strip()]
            }
        }
    }


def get_sessions() -> dict:

    events = []
    prelims_eventid = []
    eventid = 1

    # create directory to store the processed data
    pathlib.Path('processed_data').mkdir(parents=True, exist_ok=True)
    for filename in os.listdir('scraped_data/schedules/by_date'):
        file = os.path.join('scraped_data/schedules/by_date', filename)
        if os.path.isfile(file):
            with open(file, 'r') as f:
                data: list = json.loads(f.read())['e']
                for event in data:
                    infos = get_event_infos(event, eventid, filename)
                    heats = get_heats(event, eventid)
                    race = infos | heats
                    # if the event is a preliminary or heat, put race_code, eventid and -current event's- category into the prelims list
                    if race['lenex']['event']['preveventid'] == '-1':
                        prelims_eventid.append({
                            'race_code': RACE_CODES[event["d_en"]],
                            'eventid': race['lenex']['event']['eventid'],
                            'category': event['c0']
                        })
                    eventid = eventid + 1
                    events.append(race)
                f.close()

    for race in events:
        # if event has a prev_event, the parent event in the prelims list. This script is designed for 'normal' event, no semis. # TODO: handle semis (and quarters)
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

    with open('processed_data/sessions.json', 'w') as f:  # write results
        f.write(json.dumps(sessions))
        f.close()

    return sessions
