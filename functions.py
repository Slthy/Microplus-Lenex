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
import re
from datetime import date


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
                'nation': 'ITA' if data['Event']['Place'].split(',')[0] in ['Roma', 'Riccione', 'Ostia']
                else input(f'insert nation code (city: {data["Event"]["Place"].split(",")[0]}): '),
                'course': pool_length_code,
                'timing': "AUTOMATIC",
                'lanemin': '0',
                'lanemax': '9'
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


def get_relay_splits_and_athletes(entry: dict, pool_length: int, gender: str):
    """Returns the splits of a given relay and the general infos of the relay's atheletes

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
    """returns LENEX `heats` component for a given event

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
        heats = {}
        heat_entries: dict = json.loads(f.read())
        data: list = heat_entries['data']
        agegroup: dict[str, list] = {
            'id': f'10{eventid}',
            'age_costraints': {
                'agemax': '-1',
                'agemin': '-1'
            },
            'results': []
        }

        cat = heat_entries['Category']['Cod']
        if cat in utils.JUNIOR_CATEGORIES.keys():
            agegroup['age_costraints']['agemax'] = utils.JUNIOR_CATEGORIES[cat]['agemax']
            agegroup['age_costraints']['agemin'] = utils.JUNIOR_CATEGORIES[cat]['agemin']
        elif re.match(r'^\d\d[FM]$', cat): #regex ,  0, -1
            yob = int(f'20{cat[0]}{cat[1]}')
            agegroup['age_costraints']['agemax'] = str(date.today().year - yob)
            agegroup['age_costraints']['agemin'] = str(date.today().year - yob - 1)

        entries = {
            'type': 'relays' if 'Players' in data[0].keys() else 'heats',
            'data': [[], []]  # indexes: 0 for single entries, 1 for relays
        }

        result_n = 1
        # relay event --HANDLE people that only swim in relays--
        if 'Players' in data[0].keys():
            times = []
            DNFs = []
            for entry in data:
                heatid = f'{entry["b"]}000{eventid}'
                swimtime = utils.format_time(entry['MemPrest'])
                splits = get_relay_splits_and_athletes(
                    entry, pool_length, heat_entries['Category']['Cod'][-1])
                resultid = f'20{eventid}{result_n}'
                entries['data'][0].append(
                    [{'athlete_infos': a} for a in splits['player_positions']])
                entries['data'][1].append({
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
                        'agegroupid': agegroup['id'],
                        'resultid': resultid,
                        'place': entry['PlaCls'],  # TODO! place
                        'lane': entry['PlaLane'],
                        'heat': str(entry["b"]),
                        'heatid': str(heatid),
                        'swimtime': swimtime,
                        'reactiontime': '',
                        'splits': splits
                    }
                })

                if entry["b"] not in heats.keys():
                    heats[entry["b"]] = {
                        'daytime': heat_entries['Heat']['UffTime'],
                        'heatid': heatid,
                        'number': entry["b"]
                    }

                if entry['PlaCls'].isdigit():
                    times.append({'resultid': resultid, 'swimtime_float': utils.time_to_timedelta(swimtime).total_seconds()})
                else:
                    DNFs.append({'resultid': resultid, 'swimtime': entry['PlaCls']})
                result_n = result_n + 1
            
            sorted_rankings = sorted(times, key = lambda x: x['swimtime_float'])
            for index, result in enumerate(sorted_rankings):
                agegroup['results'].append({
                        'order': str(index + 1),
                        'place': str(index + 1),
                        'resultid': result['resultid']
                    })
            for index, dnf in enumerate(DNFs):
                agegroup['results'].append({
                        'order': str((index + 1) + len(sorted_rankings)),
                        'place': str((index + 1) + len(sorted_rankings)),
                        'resultid': dnf['resultid']
                    })
        else:  # single event
            times = []
            DNFs = []
            for entry in data:
                heatid = f'{entry["b"]}000{eventid}'
                resultid = f'20{eventid}{result_n}'
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
                swimtime = utils.format_time(entry['MemPrest'])
                swimstyle_split = event["d_en"].split('m')
                entries['data'][0].append({
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
                        'heat': str(entry["b"]),
                        'lane': entry['PlaLane'],
                        'meetinfo': heat_entries['Heat']['UffDate']
                    },
                    'result': {
                        'eventid': str(eventid),
                        'agegroupid': agegroup['id'],
                        'resultid': resultid,
                        'place': entry['PlaCls'],
                        'lane': entry['PlaLane'],
                        'heat': str(entry["b"]),
                        'heatid': heatid,
                        'swimtime': swimtime,
                        'points': str(utils.get_fina_points(swimtime, 
                                                            swimstyle_split[0].strip(), 
                                                            utils.LENEX_STROKES[swimstyle_split[1].strip()],
                                                            event["c0"][-1],
                                                            'LCM' if pool_length == 50 else 'SCM')) if swimtime != 'NT' else '',
                        'reactiontime': '',
                        'splits': splits
                    }
                })
                get_entry_time(
                    event["c0"], event["d_en"], event["c2"][::2], entry['PlaCod'])
                if entry['b'] not in heats.keys():
                    heats[str(entry["b"])] = {
                        'daytime': heat_entries['Heat']['UffTime'],
                        'heatid': heatid,
                        'number': str(entry["b"])
                    }

                if entry['PlaCls'].isdigit():
                    times.append({'resultid': resultid, 'swimtime_float': utils.time_to_timedelta(swimtime).total_seconds()})
                else:
                    DNFs.append({'resultid': resultid, 'swimtime': entry['PlaCls']})
                result_n = result_n + 1
            
            sorted_rankings = sorted(times, key = lambda x: x['swimtime_float'])
            for index, result in enumerate(sorted_rankings):
                agegroup['results'].append({
                        'order': str(index + 1),
                        'place': str(index + 1),
                        'resultid': result['resultid']
                    })
            for index, dnf in enumerate(DNFs):
                agegroup['results'].append({
                        'order': str((index + 1) + len(sorted_rankings)),
                        'place': str((index + 1) + len(sorted_rankings)),
                        'resultid': dnf['resultid']
                    })


    return {'heats': dict(sorted(heats.items())), 'agegroup': agegroup, 'entries': entries}


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
                    heats_data = get_heats(event, eventid, pool_length)
                    infos = get_event_infos(event, eventid, filename) | {
                        'agegroup': heats_data['agegroup']}
                    race = infos | {'heats': heats_data['heats']}
                    if heats_data['entries']['type'] == 'heats':
                        entries['athletes'] += heats_data['entries']['data'][0]
                    else:
                        for athlete in heats_data['entries']['data'][0]:
                            entries['athletes'] += athlete
                        entries['relays'] += heats_data['entries']['data'][1]
                    # if the event is a preliminary or heat, put race_code, eventid and -current event's- category into the prelims list
                    if race['lenex']['event']['preveventid'] == '-1':
                        prelims_eventid.append({
                            'race_code': utils.RACE_CODES[event["d_en"]],
                            'eventid': race['lenex']['event']['eventid'],
                            'category': event['c0']
                        })
                    eventid = eventid + 1
                    # if event has a prev_event, the parent event in the prelims list. This script is designed for 'normal' event, no semis. # TODO: #8 handle semis (and quarters)
                    if race['lenex']['event']['preveventid'] == '00':
                        for prelim in prelims_eventid:
                            if prelim['race_code'] == race['race_code'] and prelim['category'] == race['category']:
                                race['lenex']['event']['preveventid'] = prelim['eventid']
                    events.append(race)

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
        # TODO: refactoring
        if club_name not in clubs.keys():  # new club
            club_infos = infos['team']
            del infos['team']
            clubs[club_name] = {
                'infos': club_infos,
                'athletes': {
                    athleteid: {'athlete_infos': infos}
                },
                'relays': []
            }
            if len(entry.keys()) > 1:  # athlete has entries and results
                clubs[club_name]['athletes'][athleteid]['entries'] = [
                    entry['entry']]
                clubs[club_name]['athletes'][athleteid]['results'] = [
                    entry['result']]

        # club already in 'clubs' dict, new athlete to add
        elif athleteid not in clubs[club_name]['athletes'].keys():
            del infos['team']
            clubs[club_name]['athletes'][athleteid] = {'athlete_infos': infos}
            if len(entry.keys()) > 1:  # athlete has entries and results
                clubs[club_name]['athletes'][athleteid]['entries'] = [
                    entry['entry']]
                clubs[club_name]['athletes'][athleteid]['results'] = [
                    entry['result']]
        else:  # both club and athlete are in the c/a dicts, append new data to 'entries' and 'results' field

            try:
                if len(entry.keys()) > 1:  # athlete has entries and result
                    clubs[club_name]['athletes'][athleteid]['entries'].append(
                        entry['entry'])
                    clubs[club_name]['athletes'][athleteid]['results'].append(
                        entry['result'])
            except KeyError:  # the first at
                clubs[club_name]['athletes'][athleteid]['entries'] = [
                    entry['entry']]
                clubs[club_name]['athletes'][athleteid]['results'] = [
                    entry['result']]

    for entry in entries['relays']:
        club_name = entry['relay_infos']['team']['name']

        if club_name not in clubs.keys():  # new club
            clubs[club_name] = {
                'infos': entry['relay_infos']['team'],
                'athletes': {},
                'relays': [entry]
            }
            for athlete in entry['result']['splits']['player_positions']:
                clubs[club_name]['athletes'][athleteid] = {
                    'athlete_infos': athlete
                }
        else:
            clubs[club_name]['relays'].append(entry)

    return {'sessions': sessions, 'clubs': clubs}


def build_lenex() -> str:
    """Main function, elaborates and compile data into a `XML` string

    Returns:
        dict: compiled data
            Keys:
                -`xml`: a string containing the xml file to be written
                -`event_name`: event's name and xml's filename
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
        'lanemin': data['event']['lanemin'],
        'lanemax': data['event']['lanemax']
    })
    ET.SubElement(meet, "POINTTABLE", {
        'name': 'FINA Point Scoring',
        'version': '2023'
    })
    sessions = ET.SubElement(meet, "SESSIONS")
    for n in data['sessions'].keys():
        session_data = data['sessions'][n]
        session = ET.SubElement(sessions, "SESSION", {
            'number': session_data['infos']['number'],
            'date': session_data['infos']['date'],
            'daytime': session_data['infos']['daytime']
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
            agegroups = ET.SubElement(event, "AGEGROUPS")
            agegroup = ET.SubElement(agegroups, "AGEGROUP", {
                'agegroupid': e['agegroup']['id'],
                'agemax': e['agegroup']['age_costraints']['agemax'],
                'agemin': e['agegroup']['age_costraints']['agemin']
            })
            rankings = ET.SubElement(agegroup, "RANKINGS")
            for r in e['agegroup']['results']:
                ET.SubElement(rankings, "RANKING", {
                    'order': r['order'],
                    'place': r['place'],
                    'resultid': r['resultid']
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
            'name': requests.utils.unquote(club_infos['name']),
            'code': requests.utils.unquote(club_infos['code']),
            'nation': club_infos['nation'],
            'type': club_infos['type']
        })
        athletes = ET.SubElement(club, "ATHLETES")
        club_athletes = data['clubs'][c]['athletes']
        for a in club_athletes.keys():
            athlete_infos = club_athletes[a]['athlete_infos']
            athlete = ET.SubElement(athletes, "ATHLETE", {
                'athleteid': athlete_infos['athleteid'],
                'lastname': requests.utils.unquote(athlete_infos['lastname']),
                'firstname': requests.utils.unquote(athlete_infos['firstname']),
                'gender': athlete_infos['gender'],
                'birthdate': f"{athlete_infos['birthdate']}-01-01"
            })
            if 'entries' in club_athletes[a].keys():
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
                        'resultid': r['resultid'],
                        'place': r['place'],
                        'lane': r['lane'],
                        'heat': r['heat'],
                        'heatid': r['heatid'],
                        'swimtime': r['swimtime'],
                        'points': r['points'],
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
                relay = ET.SubElement(relays, "RELAY", {
                    'number': '1',  # only one relay per team is allowed in supported championships
                    'agemax': '-1',  # TODO: #10 handle categories in junior events
                    'agemin': '-1',  # '-1' value is default value
                    'agetotalmax': '-1',
                    'gender': r['relay_infos']['gender'],
                    'name': r['relay_infos']['team']['name']
                })
                results = ET.SubElement(relay, "RESULTS")

                result = ET.SubElement(results, "RESULT", {
                    'eventid': r['result']['eventid'],
                    'resultid': r['result']['resultid'],
                    'place': r['result']['place'],
                    'lane': r['result']['lane'],
                    'heat': r['result']['heat'],
                    'heatid': r['result']['heatid'],
                    'swimtime': r['result']['swimtime'],
                    'reactiontime': r['result']['reactiontime']
                })
                splits = ET.SubElement(result, "SPLITS")
                for s in r['result']['splits']['data']:
                    ET.SubElement(splits, "SPLIT", {
                        'distance': s['distance'],
                        'swimtime': s['swimtime']
                    })

                player_positions = ET.SubElement(result, "RELAYPOSITIONS")
                for p in r['result']['splits']['player_positions']:
                    ET.SubElement(player_positions, "RELAYPOSITION", {
                        'number': p['number'],
                        'athleteid': p['athleteid'],
                        'reactiontime': p['reactiontime']
                    })

    dom = xml.dom.minidom.parseString(ET.tostring(root))
    xml_string = dom.toprettyxml()
    part1, part2 = xml_string.split('?>')
    output_xml = part1 + 'encoding=\"{}\" standalone="no"?>\n'.format('utf-8') + part2
    event_name = data['event']['name']

    return {
        'xml': output_xml,
        'event_name': event_name.replace(' ', '_')
    }


def write_file(data: dict):
    with open(f"processed_data/{data['event_name']}.lef", 'w') as xfile:
        xfile.write(data['xml'])


def debug(data: dict):
    with open(f"processed_data/lenex_refactor.lef", 'w') as xfile:
        xfile.write(data['xml'])
    print(
        f'check: {filecmp.cmp("processed_data/lenex_refactor.lef", "processed_data/lenex.lef", shallow=False)}')
