import xml.etree.cElementTree as ET
import xml.dom.minidom
import json


with open('processed_data/lenex_data.json', 'r') as f:
    data = json.loads(f.read())
    m_encoding = 'utf-8'
    root = ET.Element("LENEX", version="3.0")
    constructor = ET.SubElement(root, "CONSTRUCTOR", name=data['constructor']['name'])
    ET.SubElement(constructor, "CONTACT", {
        'name' : data['constructor']['name'], 
        'zip' : data['constructor']['zip'],
        'city' : data['constructor']['city'],
        'email' : data['constructor']['email'],
        'internet' : data['constructor']['internet'],
    })
    meets = ET.SubElement(root, "MEETS")
    meet = ET.SubElement(meets, "MEET", {
        'name' : data['event']['name'],
        'city' : data['event']['city'],
        'nation' : data['event']['nation'],
        'course' : data['event']['course'],
        'timing' : data['event']['timing']
    })
    pool = ET.SubElement(meet, "POOL", {
        'pool_lane_min' : data['event']['pool_lane_min'],
        'pool_lane_max' : data['event']['pool_lane_max']
    })
    pointtable = ET.SubElement(meet, "POINTTABLE", {
        'name' : 'FINA Point Scoring',
        'version' : '2004'
    })
    sessions = ET.SubElement(meet, "SESSIONS")
    for n in data['sessions'].keys():
        session_data = data['sessions'][n]
        session = ET.SubElement(sessions, "SESSION", {
            'number' : session_data['infos']['number'],
            'date' : session_data['infos']['date'],
            'daytime' : session_data['infos']['daytime']
        })
        pool2 = ET.SubElement(session, "POOL", {
        'pool_lane_min' : data['event']['pool_lane_min'],
        'pool_lane_max' : data['event']['pool_lane_max']
        })
        events = ET.SubElement(session, "EVENTS")
        for e in session_data['events']:
            event = ET.SubElement(events, "EVENT", {
                'eventid' : e['lenex']['event']['eventid'],
                'number' : e['lenex']['event']['number'],
                'preveventid' : e['lenex']['event']['preveventid'],
                'gender' : e['lenex']['event']['gender'],
                'round' : e['lenex']['event']['round'],
                'daytime' : e['lenex']['event']['daytime']
            })
            swimstyle = ET.SubElement(event, "SWIMSTYLE", {
                'distance' : e['lenex']['swimstyle']['distance'],
                'relaycount' : e['lenex']['swimstyle']['relaycount'],
                'stroke' : e['lenex']['swimstyle']['stroke']
            })
            heats = ET.SubElement(event, "HEATS")
            for h in e['heats'].keys():
                heats_data = e['heats'][h]
                heat = ET.SubElement(heats, "HEAT", {
                    'daytime' : e['heats'][h]['daytime'],
                    'heatid' : e['heats'][h]['heatid'],
                    'number' : e['heats'][h]['number'],
                })
    
    clubs = ET.SubElement(meet, "CLUBS")
    for c in data['clubs'].keys():
        club_infos = data['clubs'][c]['infos']
        club = ET.SubElement(clubs, "CLUB", {
            'name' : club_infos['name'],
            'shortname' : club_infos['shortname'],
            'code' : club_infos['code'],
            'nation' : club_infos['nation'],
            'type' : club_infos['type']
        })
        athletes = ET.SubElement(club, "ATHLETES")
        for a in data['clubs'][c]['athletes'].keys():
            athlete_infos = data['clubs'][c]['athletes'][a]['athlete_infos']
            athlete = ET.SubElement(athletes, "ATHLETE", {
                'athleteid' : athlete_infos['athleteid'],
                'lastname' : athlete_infos['lastname'],
                'firstname' : athlete_infos['firstname'],
                'gender' : athlete_infos['gender'],
                'birthdate' : athlete_infos['birthdate']
            })
            entries = ET.SubElement(athlete, "ENTRIES")
            for e in data['clubs'][c]['athletes'][a]['entries']:
                entry = ET.SubElement(entries, "ENTRY", {
                    'entrytime' : e['entrytime'],
                    'eventid' : e['eventid'],
                    'heat' : e['heat'],
                    'lane' : e['lane']
                })
                meetinfo = ET.SubElement(entry, "MEETINFO", date=e['meetinfo'])
            results = ET.SubElement(athlete, "RESULTS")
            for r in data['clubs'][c]['athletes'][a]['results']:
                result = ET.SubElement(results, "RESULT", {
                    'eventid' : r['eventid'],
                    'place' : r['place'],
                    'lane' : r['lane'],
                    'heat' : r['heat'],
                    'heatid' : r['heatid'],
                    'swimtime' : r['swimtime'],
                    'reactiontime' : r['reactiontime']
                })
                splits = ET.SubElement(result, "SPLITS")
                for s in r['splits']:
                    split = ET.SubElement(splits, "SPLIT", {
                        'distance' : s['distance'],
                        'swimtime' : s['swimtime']
                    })
    
    dom = xml.dom.minidom.parseString(ET.tostring(root))
    xml_string = dom.toprettyxml()
    part1, part2 = xml_string.split('?>')

    with open("FILE.xml", 'w') as xfile:
        xfile.write(part1 + 'encoding=\"{}\" standalone="no"?>\n'.format(m_encoding) + part2)
        xfile.close()