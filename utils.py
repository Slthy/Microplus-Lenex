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

JUNIOR_CATEGORIES = {
    "CAF" : {
        'agemax': '17',
        'agemin': '18'
    },
    "CAM" : {
        'agemax': '20',
        'agemin': '19'
    },
    "JUF" : {
        'agemax': '15',
        'agemin': '16'
    },
    "JUM" : {
        'agemax': '18',
        'agemin': '17'
    },
    "RAF" : {
        'agemax': '13',
        'agemin': '14'
    },
    "RAM" : {
        'agemax': '16',
        'agemin': '14'
    }
}

FINA_2023_BASETIMES = {
    "50_BACK_F_LCM": 26.98,
    "50_BACK_F_SCM": 25.27,
    "50_BACK_M_LCM": 23.8,
    "50_BACK_M_SCM": 22.22,
    "50_BREAST_F_LCM": 29.3,
    "50_BREAST_F_SCM": 28.56,
    "50_BREAST_M_LCM": 25.95,
    "50_BREAST_M_SCM": 24.95,
    "50_FLY_F_LCM": 24.43,
    "50_FLY_F_SCM": 24.38,
    "50_FLY_M_LCM": 22.27,
    "50_FLY_M_SCM": 21.75,
    "50_FREE_F_LCM": 23.67,
    "50_FREE_F_SCM": 22.93,
    "50_FREE_M_LCM": 20.91,
    "50_FREE_M_SCM": 20.16,
    "100_BACK_F_LCM": 57.45,
    "100_BACK_F_SCM": 54.89,
    "100_BACK_M_LCM": 51.85,
    "100_BACK_M_SCM": 48.33,
    "100_BREAST_F_LCM": 64.13,
    "100_BREAST_F_SCM": 62.36,
    "100_BREAST_M_LCM": 56.88,
    "100_BREAST_M_SCM": 55.28,
    "100_FLY_F_LCM": 55.48,
    "100_FLY_F_SCM": 54.59,
    "100_FLY_M_LCM": 49.45,
    "100_FLY_M_SCM": 47.78,
    "100_FREE_F_LCM": 51.71,
    "100_FREE_F_SCM": 50.25,
    "100_FREE_M_LCM": 46.91,
    "100_FREE_M_SCM": 44.84,
    "100_MEDLEY_F_SCM": 56.51,
    "100_MEDLEY_M_SCM": 49.28,
    "200_BACK_F_LCM": 123.35,
    "200_BACK_F_SCM": 118.94,
    "200_BACK_M_LCM": 111.92,
    "200_BACK_M_SCM": 105.63,
    "200_BREAST_F_LCM": 138.95,
    "200_BREAST_F_SCM": 134.57,
    "200_BREAST_M_LCM": 126.12,
    "200_BREAST_M_SCM": 120.16,
    "200_FLY_F_LCM": 121.81,
    "200_FLY_F_SCM": 119.61,
    "200_FLY_M_LCM": 110.73,
    "200_FLY_M_SCM": 108.24,
    "200_FREE_F_LCM": 112.98,
    "200_FREE_F_SCM": 110.31,
    "200_FREE_M_LCM": 102,
    "200_FREE_M_SCM": 99.37,
    "200_MEDLEY_F_LCM": 126.12,
    "200_MEDLEY_F_SCM": 121.86,
    "200_MEDLEY_M_LCM": 114,
    "200_MEDLEY_M_SCM": 109.63,
    "400_FREE_F_LCM": 236.46,
    "400_FREE_F_SCM": 233.92,
    "400_FREE_M_LCM": 220.07,
    "400_FREE_M_SCM": 212.25,
    "400_MEDLEY_F_LCM": 266.36,
    "400_MEDLEY_F_SCM": 258.94,
    "400_MEDLEY_M_LCM": 243.84,
    "400_MEDLEY_M_SCM": 234.81,
    "800_FREE_F_LCM": 484.79,
    "800_FREE_F_SCM": 479.34,
    "800_FREE_M_LCM": 452.12,
    "800_FREE_M_SCM": 443.42,
    "1500_FREE_F_LCM": 920.48,
    "1500_FREE_F_SCM": 918.01,
    "1500_FREE_M_LCM": 871.02,
    "1500_FREE_M_SCM": 846.88
}


time_to_timedelta = lambda t : datetime.strptime(t, "%H:%M:%S.%f") - datetime(1900,1,1)
def get_fina_points(time: int, race_length: str, discipline: str, gender: str, course: str):
    basetime = FINA_2023_BASETIMES[f'{race_length}_{discipline}_{gender}_{course}']
    time_float = time_to_timedelta(time).total_seconds()
    return round(1000*(basetime/time_float)**3)

    
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
