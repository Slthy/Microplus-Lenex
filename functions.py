import requests
import json
import pathlib
import os
import datetime
import utils
import inquirer
import xml.etree.cElementTree as ET
import xml.dom.minidom

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
        pool_length_code = inquirer.prompt([inquirer.List('length', message="Pool Length", choices=[
            'SCM', 'LCM'])])['length']
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
                'course': pool_length_code,  # TODO: #2 check?, inquirer module
                'timing': "AUTOMATIC",
                'pool_lane_min': '0',
                'pool_lane_max': '10'
            },
            'pool_length': 50 if pool_length_code == 'LCM' else 25
        }


# returns the entry time in an event for a given athlete
def get_entry_time(category: str, race_code, event_type: str, PlaCod: str) -> str:
    with open(f'scraped_data/startlists/NU{category}{utils.RACE_CODES[race_code]}STAR{event_type} 001.JSON', 'r') as f:
        for entry in json.loads(f.read())['data']:
            if entry['PlaCod'] == PlaCod:
                return utils.format_time(entry['MemIscr'])


# returns LENEX 'heats' component for the given event and all the athlete entries
def get_heats(event: dict, eventid: int, pool_length: int) -> dict:
    with open(f'scraped_data/results/NU{event["c0"]}{utils.RACE_CODES[event["d_en"]]}CLAS{event["c2"][::2]} 001.JSON', 'r') as f:
        heat_entries: list = json.loads(f.read())
        data: list = heat_entries['data']
        athlete_entries = []
        heats = {}
        heat_n = 1
        for entry in data:
            entrytime = get_entry_time(
                event["c0"], event["d_en"], event["c2"][::2], entry['PlaCod'])
            # 'heatid' is composed of the heat's at the head, eventid at the tail, filled in between by '0's
            heatid = f'{heat_n}{"0"*(5-(len(str(heat_n)) + len(str(eventid))))}{eventid}'
            swimtime = utils.format_time(entry['MemPrest'])
            splits = []
            # first element is blank every time, so we cut it
            for index, time in enumerate(entry['MemFields'][1:]):
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
                    'eventid': str(eventid),
                    'entrytime': entrytime,
                    'heat': entry['b'],
                    'lane': entry['PlaLane'],
                    'meetinfo': heat_entries['Heat']['UffDate']
                },
                'result': {
                    'eventid': str(eventid),
                    'place': entry['PlaCls'],
                    'lane': entry['PlaLane'],
                    'heat': str(heat_n),
                    'heatid': str(heatid),
                    'swimtime': swimtime,
                    'reactiontime': '',  # TODO: #6 check if value is given in other microplus events
                    'splits': splits
                }
            })
            if entry['b'] not in heats.keys():
                heats[entry['b']] = {
                    # TODO: #7 check for possible bug regarding this field, sometimes is empty
                    'daytime': heat_entries['Heat']['UffTime'],
                    # heatid is by default 5 char long, composed by the heat's number at the start and event's id at the end, in the middle '0's fill the remaining chars
                    'heatid': heatid,
                    'number': str(heat_n)
                }
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
                    race = infos | {'heats': heats_data['heats']}
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

        if club_name not in clubs.keys():  # new club
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
        # club already in 'clubs' dict, new athlete to add
        elif athleteid not in clubs[club_name]['athletes'].keys():
            del entry['athlete_infos']['team']

            clubs[club_name]['athletes'][athleteid] = {
                'athlete_infos': entry['athlete_infos'],
                'entries': [entry['entry']],
                'results': [entry['result']]
            }
        else:  # both club and athlete are in the respective dicts, append new data to 'entries' and 'results' field
            clubs[club_name]['athletes'][athleteid]['entries'].append(
                entry['entry'])
            clubs[club_name]['athletes'][athleteid]['results'].append(
                entry['result'])

    return {'sessions': sessions, 'clubs': clubs}


def build_lenex() -> None:
    competition_infos = get_competition_infos()
    data: dict = competition_infos | convert_to_lenex(
        competition_infos['pool_length'])
    m_encoding = 'utf-8'
    root = ET.Element("LENEX", version="3.0")
    constructor = ET.SubElement(
        root, "CONSTRUCTOR", name=data['constructor']['name'])
    ET.SubElement(constructor, "CONTACT", {
        'name': data['constructor']['name'],
        'zip': data['constructor']['zip'],
        'city': data['constructor']['city'],
        'email': data['constructor']['email'],
        'internet': data['constructor']['internet'],
    })
    meets = ET.SubElement(root, "MEETS")
    meet = ET.SubElement(meets, "MEET", {
        'name': data['event']['name'],
        'city': data['event']['city'],
        'nation': data['event']['nation'],
        'course': data['event']['course'],
        'timing': data['event']['timing']
    })
    ET.SubElement(meet, "POOL", {
        'pool_lane_min': data['event']['pool_lane_min'],
        'pool_lane_max': data['event']['pool_lane_max']
    })
    ET.SubElement(meet, "POINTTABLE", {
        'name': 'FINA Point Scoring',
        'version': '2004'
    })
    sessions = ET.SubElement(meet, "SESSIONS")
    for n in data['sessions'].keys():
        session_data = data['sessions'][n]
        session = ET.SubElement(sessions, "SESSION", {
            'number': session_data['infos']['number'],
            'date': session_data['infos']['date'],
            'daytime': session_data['infos']['daytime']
        })
        ET.SubElement(session, "POOL", {
            'pool_lane_min': data['event']['pool_lane_min'],
            'pool_lane_max': data['event']['pool_lane_max']
        })
        events = ET.SubElement(session, "EVENTS")
        for e in session_data['events']:
            event = ET.SubElement(events, "EVENT", {
                'eventid': e['lenex']['event']['eventid'],
                'number': e['lenex']['event']['number'],
                'preveventid': e['lenex']['event']['preveventid'],
                'gender': e['lenex']['event']['gender'],
                'round': e['lenex']['event']['round'],
                'daytime': e['lenex']['event']['daytime']
            })
            ET.SubElement(event, "SWIMSTYLE", {
                'distance': e['lenex']['swimstyle']['distance'],
                'relaycount': e['lenex']['swimstyle']['relaycount'],
                'stroke': e['lenex']['swimstyle']['stroke']
            })
            heats = ET.SubElement(event, "HEATS")
            for h in e['heats'].keys():
                e['heats'][h]
                ET.SubElement(heats, "HEAT", {
                    'daytime': e['heats'][h]['daytime'],
                    'heatid': e['heats'][h]['heatid'],
                    'number': e['heats'][h]['number'],
                })

    clubs = ET.SubElement(meet, "CLUBS")
    for c in data['clubs'].keys():
        club_infos = data['clubs'][c]['infos']
        club = ET.SubElement(clubs, "CLUB", {
            'name': club_infos['name'],
            'shortname': club_infos['shortname'],
            'code': club_infos['code'],
            'nation': club_infos['nation'],
            'type': club_infos['type']
        })
        athletes = ET.SubElement(club, "ATHLETES")
        for a in data['clubs'][c]['athletes'].keys():
            athlete_infos = data['clubs'][c]['athletes'][a]['athlete_infos']
            athlete = ET.SubElement(athletes, "ATHLETE", {
                'athleteid': athlete_infos['athleteid'],
                'lastname': athlete_infos['lastname'],
                'firstname': athlete_infos['firstname'],
                'gender': athlete_infos['gender'],
                'birthdate': athlete_infos['birthdate']
            })
            entries = ET.SubElement(athlete, "ENTRIES")
            for e in data['clubs'][c]['athletes'][a]['entries']:
                entry = ET.SubElement(entries, "ENTRY", {
                    'entrytime': e['entrytime'],
                    'eventid': e['eventid'],
                    'heat': e['heat'],
                    'lane': e['lane']
                })
                ET.SubElement(entry, "MEETINFO", date=e['meetinfo'])
            results = ET.SubElement(athlete, "RESULTS")
            for r in data['clubs'][c]['athletes'][a]['results']:
                result = ET.SubElement(results, "RESULT", {
                    'eventid': r['eventid'],
                    'place': r['place'],
                    'lane': r['lane'],
                    'heat': r['heat'],
                    'heatid': r['heatid'],
                    'swimtime': r['swimtime'],
                    'reactiontime': r['reactiontime']
                })
                splits = ET.SubElement(result, "SPLITS")
                for s in r['splits']:
                    ET.SubElement(splits, "SPLIT", {
                        'distance': s['distance'],
                        'swimtime': s['swimtime']
                    })

    dom = xml.dom.minidom.parseString(ET.tostring(root))
    xml_string = dom.toprettyxml()
    part1, part2 = xml_string.split('?>')

    with open("processed_data/lenex.lef", 'w') as xfile:
        xfile.write(
            part1 + 'encoding=\"{}\" standalone="no"?>\n'.format(m_encoding) + part2)
        xfile.close()
