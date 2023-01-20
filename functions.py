import requests
import json
import pathlib
import os
import datetime
import utils
import inquirer
import xml.etree.cElementTree as ET
import xml.dom.minidom
import filecmp


def scrape_data(url: str) -> None:
    """Main scraping function.

    Args:
        url (str): given by the user
    Returns:
        None, files are stored automatically in the right folders, execution halts if code fails.
    """
    
    url = url.replace('/NU', '/export/NU').replace('_web.php', '')
    counter_generale = requests.get(
        f'{url}/NU/CounterGenerale.json?').text[:-2]
    contatori = requests.get(
        f'{url}/NU/Contatori.json?x={counter_generale}').json()['contatori']

    for obj in contatori:
        # download json
        scraped_data = requests.get(
            f'{url}/NU/{obj["nomefile"]}?x={obj["counter"]}').json()

        # assigns a category to the downloaded json. This category will also be part of its filepath
        file_type = utils.FILE_TYPES.get(obj['cod'], "other")

        # create directory for a new type of file
        pathlib.Path(
            f'scraped_data/{file_type}').mkdir(parents=True, exist_ok=True)

        # write file into category path
        with open(f'scraped_data/{file_type}/{scraped_data["jsonfilename"]}', 'w') as f:
            f.write(json.dumps(scraped_data))


def get_competition_infos() -> dict:
    """Reads the first `JSON` file in the `scraped_data/result` direcory, retrieves competition's generic data and asks to the user the missing infos.

    Returns:
        dict: competition's infos
    """
    with open(f"scraped_data/results/{os.listdir('scraped_data/results')[0]}", 'r') as f:
        data = json.loads(f.read())
        pool_length_code = inquirer.prompt([inquirer.List('length', message="Pool Length", choices=[
            'SCM', 'LCM'])])['length']
        return {  # this script is specifically designed to scrape data from Microplus' systems
            'constructor': {
                'name': 'Microplus Informatica Srl',
                'registration': 'Scraped and Ecoded by Alessandro Borsato, gh: @Slthy, tw: @aborsato_',
                'version': '1.0',
                'CONTACT': {
                    'city': 'Marene',
                    'zip': 'IT-12030',
                    'country': 'ITA',
                    'email': 'mbox@microplus.it',
                    'internet': 'https://www.microplus.it'
                }
            },
            'event': {  # generic data about the competition's venue
                'name': data['Export']['ExpName'],
                'desciption': data['Export']['ExpDescr'],
                'city': data['Event']['Place'].split(',')[0],
                'nation': 'ITA' if data['Event']['Place'].split(',')[0] == 'Roma'
                else input(f'insert nation (city: {data["Event"]["Place"].split(",")[0]}): '),
                'course': pool_length_code,
                'timing': "AUTOMATIC",
                'pool_lane_min': '0',
                'pool_lane_max': '10'
            },
            'pool_length': 50 if pool_length_code == 'LCM' else 25
        }


def get_entry_time(category: str, race_code: str, event_type: str, PlaCod: str) -> str:
    """Returns the entry time in an event for a given athlete.

    Args:
        category (str): `athlete`'s category
        race_code (str): `event`'s race code
        event_type (str): `event`'s event type
        PlaCod (str): `athlete` id

    Returns:
        str: `athlete`'s entrytime
    """
    with open(f'scraped_data/startlists/NU{category}{utils.RACE_CODES[race_code]}STAR{event_type} 001.JSON', 'r') as f:
        for entry in json.loads(f.read())['data']:
            if entry['PlaCod'] == PlaCod:
                return utils.format_time(entry['MemIscr'])


def get_relay_splits(entry: dict, pool_length: int, gender: str):
    """Returns the splits of a given relay

    Args:
        entry (dict): relay informations
        pool_length (int): pool length
        gender (str): relay gender
            Possible Values:
                -`M`: male event
                -`F`: female event
                -`X`: mixed event

    Returns:
        dict: relay's splits
    """
    splits = []
    player_positions = []
    for player in entry['Players']:
        player_positions.append({
            'number': str(len(player_positions) + 1),
            'athleteid': player['PlaCod'],
            'reactiontime': player['PlaRT'],
            'lastname': player['PlaSurname'],
            'firstname': player['PlaName'],
            'gender': gender,
            'birthdate': player['PlaBirth'],
            'team': {
                'name': entry['TeamDescrIta'],
                'shortname': entry['TeamDescrItaVis'],
                'code': entry['PlaNat'],
                'nation': entry['PlaNat'],
                'type': 'CLUB'  # hardcoded
            }
        })
        player_splits = []
        for i in range(1, 5):
            if player[f'PlaInt{i}'] == '':
                continue
            player_splits.append(utils.format_time(player[f'PlaInt{i}']))
        if len(splits) < 4:
            splits = player_splits
        else:
            for i in range(len(player_splits)):
                t1 = splits[-1]
                t2 = player_splits[i]
                if i == 0:
                    splits.append(utils.add_times(t1, t2, "00:00:00.00"))
                else:
                    splits.append(utils.add_times(t1, t2, player_splits[i-1]))
    return {
        'data': [{
            'distance': str(pool_length*index + pool_length),
            'swimtime': splits[index-1],
        } for index in range(len(splits))],
        'player_positions': player_positions
    }  # in athlete, only entry, no result <ENTRY entrytime="NT" eventid="48" />


def get_heats(event: dict, eventid: int, pool_length: int) -> dict:
    """returns LENEX `heats` component all the athlete entries for a given event

    Args:
        event (dict): `event` dictionary
        eventid (int): event id
        pool_length (int): pool length

    Returns:
        dict: a dictionary with two keys
            Keys:
                -`heats`: heats in the given event
                -`entries`: dict
                    Keys:
                        -`data`: `entries`' data
                        `type`: `entries`' type
                            Possible values:
                                -`relays`: relay event
                                -`heats`: single event
    """
    with open(f'scraped_data/results/NU{event["c0"]}{utils.RACE_CODES[event["d_en"]]}CLAS{event["c2"][::2]} 001.JSON', 'r') as f:
        heat_entries: dict = json.loads(f.read())
        data: list = heat_entries['data']
        entries = {
            'type': 'relays' if 'Players' in data[0].keys() else 'heats',
            'data': []
        }
        heats = {}
        heat_n = 1
        for entry in data:
            # 'heatid' is composed of the heat's number at the head and eventid at the end
            heatid = f'{heat_n}000{eventid}'
            if 'Players' in entry.keys():  # relay event
                splits = get_relay_splits(
                    entry, pool_length, heat_entries['Category']['Cod'][-1])
                athletes = []
                relay = ({
                    'relay_infos': {
                        'gender': event["c0"][-1] if event["c0"][-1] in ['M', 'F'] else 'X',
                        'team': {
                            'name': entry['TeamDescrIta'],
                            'code': entry['PlaTeamCod'],
                            'nation': entry['PlaNat'],
                            'type': 'CLUB'  # hardcoded
                        }
                    },
                    'result': {
                        'eventid': str(eventid),
                        'place': entry['PlaCls'],
                        'lane': entry['PlaLane'],
                        'heat': str(heat_n),
                        'heatid': str(heatid),
                        'swimtime': utils.format_time(entry['MemPrest']),
                        'reactiontime': '',
                        'splits': splits
                    }
                })
                '''# append entries in athlete entry-list
                for player in splits['player_positions']:
                    athletes.append({
                        'athlete_infos': player,
                        'entry': {
                            'eventid': str(eventid),
                            'entrytime': 'NT'
                        }
                    })
                entries['data'].append({
                    'relay': relay,
                    'athletes': athletes
                })'''
            else:  # single event
                entrytime = get_entry_time(
                    event["c0"], event["d_en"], event["c2"][::2], entry['PlaCod'])
                splits = []
                # first element is blank every time, so we cut it
                for index, time in enumerate(entry['MemFields'][1:]):
                    if time['V'] == "":
                        break
                    splits.append({
                        'distance': str(pool_length*index + pool_length),
                        'swimtime': utils.format_time(time['V'])
                    })

                entries['data'].append({
                    'athlete_infos': {
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
                        'heat': str(heat_n),
                        'lane': entry['PlaLane'],
                        'meetinfo': heat_entries['Heat']['UffDate']
                    },
                    'result': {
                        'eventid': str(eventid),
                        'place': entry['PlaCls'],
                        'lane': entry['PlaLane'],
                        'heat': str(heat_n),
                        'heatid': str(heatid),
                        'swimtime': utils.format_time(entry['MemPrest']),
                        'reactiontime': '',
                        'splits': splits
                    }
                })
            if str(heat_n) not in heats.keys():
                heats[str(heat_n)] = {
                    'daytime': heat_entries['Heat']['UffTime'],
                    'heatid': heatid,
                    'number': str(heat_n)
                }
                heat_n = heat_n + 1
                
    return {'heats': dict(sorted(heats.items())), 'entries': entries}


def get_event_infos(event: dict, eventid: int, filename: str) -> dict:
    """Return competition's generic infos

    Args:
        event (dict): current `event`
        eventid (int): current `event`'s id
        filename (str): `event`'s `session` schedule file, stored in `scraped_data/schedules/by_date`

    Returns:
        dict: competition's infos
    """
    swimstyle_split = event["d_en"].split('m')
    return {
        'session': int(filename[15:-5:]),
        'category': event['c0'],
        'race_code': utils.RACE_CODES[event["d_en"]],
        'race_type': event['c2'],
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
    """Converts scraped data to match `LENEX` documentation

    Args:
        pool_length (int): pool length
        
    Returns:
        dict: converted data
            Keys:
                -`sessions`: LENEX `sessions` collection data
                -`clubs`: LENEX `clubs` collection data
    """
    
    events = []
    prelims_eventid = []
    eventid = 1
    entries = {
        'athletes': [],
        'relays': []
    }

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
                    if heats_data['entries']['type'] == 'heats':
                        entries['athletes'] += heats_data['entries']['data']
                    else:
                        entries['relays'] += heats_data['entries']['data']
                    # if the event is a preliminary or heat, put race_code, eventid and -current event's- category into the prelims list
                    if race['lenex']['event']['preveventid'] == '-1':
                        prelims_eventid.append({
                            'race_code': utils.RACE_CODES[event["d_en"]],
                            'eventid': race['lenex']['event']['eventid'],
                            'category': event['c0']
                        })
                    eventid = eventid + 1
                    events.append(race)

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

    clubs = {}
    for entry in entries['athletes']:
        infos = entry['athlete_infos']
        club_name = infos['team']['name']
        athleteid = infos['athleteid']

        if club_name not in clubs.keys():  # new club
            club_infos = infos['team']
            del infos['team']

            clubs[club_name] = {
                'infos': club_infos,
                'athletes': {
                    athleteid: {
                        'athlete_infos': infos,
                        'entries': [entry['entry']],
                        'results': [entry['result']]
                    }
                },
                'relays': []
            }
        # club already in 'clubs' dict, new athlete to add
        elif athleteid not in clubs[club_name]['athletes'].keys():
            del infos['team']

            clubs[club_name]['athletes'][athleteid] = {
                'athlete_infos': infos,
                'entries': [entry['entry']],
                'results': [entry['result']]
            }
        else:  # both club and athlete are in the c/a dicts, append new data to 'entries' and 'results' field
            clubs[club_name]['athletes'][athleteid]['entries'].append(
                entry['entry'])
            clubs[club_name]['athletes'][athleteid]['results'].append(
                entry['result'])

    for entry in entries['relays']:
        club_name = entry['relay']['relay_infos']['team']['name']

        if club_name not in clubs.keys():  # new club

            clubs[club_name] = {
                'infos': entry['relay']['relay_infos']['team'],
                'athletes': {},
                'relays': [entry]
            }
            for athlete in entry:
                clubs[club_name]['athletes'][athleteid] = {
                    'athlete_infos': athlete['athlete_infos'],
                    'entries': [athlete['entry']]
                }
        elif athleteid not in clubs[club_name]['athletes'].keys():

            for athlete in entry['athletes']:
                clubs[club_name]['athletes'][athleteid] = {
                    'athlete_infos': athlete['athlete_infos'],
                    'entries': [athlete['entry']]
                }
            clubs[club_name]['relays'].append(entry)

        else:  # both club and athlete are in the respective dicts, append new data to 'entries' and 'results' field
            clubs[club_name]['athletes'][athleteid]['entries'].append(
                athlete['entry'])
            clubs[club_name]['relays'].append(entry)

    return {'sessions': sessions, 'clubs': clubs}


def build_lenex() -> str:
    """Main function, elaborates and compile data into a `XML` string

    Returns:
        str: `XML` string containing the LENEX file
    """
    competition_infos = get_competition_infos()
    data: dict = competition_infos | convert_to_lenex(
        competition_infos['pool_length'])
    root = ET.Element("LENEX", version="3.0")
    constructor = ET.SubElement(root, 
        "CONSTRUCTOR", {
            'name': data['constructor']['name'], 
            'registration': data['constructor']['registration'],
            'version': data['constructor']['version']
        })
    ET.SubElement(constructor, "CONTACT", {
        'name': data['constructor']['name'],
        'zip': data['constructor']['CONTACT']['zip'],
        'city': data['constructor']['CONTACT']['city'],
        'country': data['constructor']['CONTACT']['country'],
        'email': data['constructor']['CONTACT']['email'],
        'internet': data['constructor']['CONTACT']['internet'],
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
        club_athletes = data['clubs'][c]['athletes']
        for a in club_athletes.keys():
            athlete_infos = club_athletes[a]['athlete_infos']
            athlete = ET.SubElement(athletes, "ATHLETE", {
                'athleteid': athlete_infos['athleteid'],
                'lastname': athlete_infos['lastname'],
                'firstname': athlete_infos['firstname'],
                'gender': athlete_infos['gender'],
                'birthdate': athlete_infos['birthdate']
            })
            entries = ET.SubElement(athlete, "ENTRIES")
            for e in club_athletes[a]['entries']:
                if 'meetinfo' in e.keys():  # single event race-entry
                    entry = ET.SubElement(entries, "ENTRY", {
                        'entrytime': e['entrytime'],
                        'eventid': e['eventid'],
                        'heat': e['heat'],
                        'lane': e['lane']
                    })
                    ET.SubElement(entry, "MEETINFO", date=e['meetinfo'])
                else:  # relay event race-entry
                    entry = ET.SubElement(entries, "ENTRY", {
                        'entrytime': e['entrytime'],
                        'eventid': e['eventid']
                    })
            # an athlete may not have reced in a signle events, but only in relays, so no results.
            if 'results' in club_athletes[a].keys():
                results = ET.SubElement(athlete, "RESULTS")
                for r in club_athletes[a]['results']:
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
        if len(data['clubs'][c]['relays']) > 0:
            relays = ET.SubElement(club, "RELAYS")
            for r in data['clubs'][c]['relays']:
                relay_data = r['relay']
                relay = ET.SubElement(relays, "RELAY", {
                    'number': '1',  # only one relay per team is allowed in supported championships
                    'agemax': '-1',  # TODO: #10 handle categories in junior events
                    'agemin': '-1',  # '-1' value is default value
                    'agetotalmax': '-1',
                    'gender': relay_data['relay_infos']['gender'],
                    'name': relay_data['relay_infos']['team']['name']
                })
                results = ET.SubElement(relay, "RESULTS")

                result = ET.SubElement(results, "RESULT", {
                    'eventid': relay_data['result']['eventid'],
                    'place': relay_data['result']['place'],
                    'lane': relay_data['result']['lane'],
                    'heat': relay_data['result']['heat'],
                    'heatid': relay_data['result']['heatid'],
                    'swimtime': relay_data['result']['swimtime'],
                    'reactiontime': relay_data['result']['reactiontime']
                })
                splits = ET.SubElement(result, "SPLITS")
                for s in relay_data['result']['splits']['data']:
                    ET.SubElement(splits, "SPLIT", {
                        'distance': s['distance'],
                        'swimtime': s['swimtime']
                    })

                player_positions = ET.SubElement(result, "RELAYPOSITIONS")
                for p in relay_data['result']['splits']['player_positions']:
                    ET.SubElement(player_positions, "RELAYPOSITION", {
                        'number': p['number'],
                        'athleteid': p['athleteid'],
                        'reactiontime': p['reactiontime']
                    })

    dom = xml.dom.minidom.parseString(ET.tostring(root))
    xml_string = dom.toprettyxml()
    part1, part2 = xml_string.split('?>')

    return part1 + 'encoding=\"{}\" standalone="no"?>\n'.format('utf-8') + part2


def write_file(xml_data: str):
    with open("processed_data/lenex.lef", 'w') as xfile:
        xfile.write(xml_data)


def debug(xml_data: str):
    with open("processed_data/lenex_refactor.lef", 'w') as xfile:
        xfile.write(xml_data)
    print(
        f'check: {filecmp.cmp("processed_data/lenex_refactor.lef", "processed_data/lenex.lef", shallow=False)}')
