import requests
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Optional
from datetime import datetime


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

def swrid(lastname: str, firstname: str) -> Optional[str]: #query-search athlete through swimrakings.net, returns its swrid (swimrakings id)
    html_res = requests.get(
        f'https://www.swimrankings.net/index.php?&internalRequest=athleteFind&athlete_clubId=-1&athlete_gender=-1&athlete_lastname={lastname}&athlete_firstname={firstname}')
    url: str = BeautifulSoup(html_res.text, features="html.parser").find('a', href=True)['href']
    return parse_qs(urlparse(url).query).get('athleteId', [None])[0]

def format_time(time: str) -> str:
    # Time too short, invalid (e.g. "dnf")
    if '*' in time: # remove '*' from entrytimes
        time = time.replace('*', '')
        
    if len(time) < 4:
        return "NT"
    
    if len(time) > 5:  # time with minutes, seconds, decimals
        return datetime.strptime(time, "%M'%S.%f").strftime("%H:%M:%S.%f")[:-4]
    
    return datetime.strptime(time, "%S.%f").strftime("%H:%M:%S.%f")[:-4]


def add_times(t1, t2, time_zero) -> str:
    t1 = datetime.strptime(t1, '%H:%M:%S.%f')
    t2 = datetime.strptime(t2, '%H:%M:%S.%f')
    time_zero = datetime.strptime(time_zero, '%H:%M:%S.%f')
    result = str((t2 - time_zero + t1).time())
    if len(result) == 8: #no decimals
        result = datetime.strptime(result, "%H:%M:%S").strftime("%H:%M:%S.%f")
    return result[:-4]
