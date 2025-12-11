"""
Utility classes for time formatting, FINA points calculation, etc.
"""
from datetime import datetime, timedelta
import hashlib
import base64
class TimeUtils:
    """Utilities for time formatting and manipulation."""
    
    @staticmethod
    def format_time(time: str) -> str:
        """
        Format time string to HH:MM:SS.ss format.
        
        Args:
            time: Time string in various formats
            
        Returns:
            Formatted time string or 'NT' for invalid times
        """
        if '*' in time:
            time = time.replace('*', '')
        
        if len(time) < 4:
            return "NT"
        
        try:
            if len(time) > 5:  # Format: MM'SS.ss
                return datetime.strptime(time, "%M'%S.%f").strftime("%H:%M:%S.%f")[:-4]
            else:  # Format: SS.ss
                return datetime.strptime(time, "%S.%f").strftime("%H:%M:%S.%f")[:-4]
        except (ValueError, AttributeError):
            return "NT"
    
    @staticmethod
    def time_to_timedelta(time_str: str) -> timedelta:
        """
        Convert time string to timedelta.
        
        Args:
            time_str: Time in format HH:MM:SS.ss
            
        Returns:
            timedelta object
        """
        t = datetime.strptime(time_str, "%H:%M:%S.%f")
        return t - datetime(1900, 1, 1)
    
    @staticmethod
    def add_times(t1: str, t2: str, time_zero: str = "00:00:00.00") -> str:
        """
        Add two times together.
        
        Args:
            t1: First time
            t2: Second time
            time_zero: Base time to subtract from t2
            
        Returns:
            Sum of times in HH:MM:SS.ss format
        """
        t1_dt = datetime.strptime(t1, '%H:%M:%S.%f')
        t2_dt = datetime.strptime(t2, '%H:%M:%S.%f')
        time_zero_dt = datetime.strptime(time_zero, '%H:%M:%S.%f')
        
        result = str((t2_dt - time_zero_dt + t1_dt).time())
        
        if len(result) == 8:  # No decimals
            result = datetime.strptime(result, "%H:%M:%S").strftime("%H:%M:%S.%f")
        
        return result[:-4]


class FinaPoints:
    """Calculator for FINA/World Aquatics points."""
    
    # FINA 2023 base times
    BASE_TIMES = {
        "50_BACK_F_LCM": 26.98, "50_BACK_F_SCM": 25.27,
        "50_BACK_M_LCM": 23.8, "50_BACK_M_SCM": 22.22,
        "50_BREAST_F_LCM": 29.3, "50_BREAST_F_SCM": 28.56,
        "50_BREAST_M_LCM": 25.95, "50_BREAST_M_SCM": 24.95,
        "50_FLY_F_LCM": 24.43, "50_FLY_F_SCM": 24.38,
        "50_FLY_M_LCM": 22.27, "50_FLY_M_SCM": 21.75,
        "50_FREE_F_LCM": 23.67, "50_FREE_F_SCM": 22.93,
        "50_FREE_M_LCM": 20.91, "50_FREE_M_SCM": 20.16,
        "100_BACK_F_LCM": 57.45, "100_BACK_F_SCM": 54.89,
        "100_BACK_M_LCM": 51.85, "100_BACK_M_SCM": 48.33,
        "100_BREAST_F_LCM": 64.13, "100_BREAST_F_SCM": 62.36,
        "100_BREAST_M_LCM": 56.88, "100_BREAST_M_SCM": 55.28,
        "100_FLY_F_LCM": 55.48, "100_FLY_F_SCM": 54.59,
        "100_FLY_M_LCM": 49.45, "100_FLY_M_SCM": 47.78,
        "100_FREE_F_LCM": 51.71, "100_FREE_F_SCM": 50.25,
        "100_FREE_M_LCM": 46.91, "100_FREE_M_SCM": 44.84,
        "100_MEDLEY_F_SCM": 56.51, "100_MEDLEY_M_SCM": 49.28,
        "200_BACK_F_LCM": 123.35, "200_BACK_F_SCM": 118.94,
        "200_BACK_M_LCM": 111.92, "200_BACK_M_SCM": 105.63,
        "200_BREAST_F_LCM": 138.95, "200_BREAST_F_SCM": 134.57,
        "200_BREAST_M_LCM": 126.12, "200_BREAST_M_SCM": 120.16,
        "200_FLY_F_LCM": 121.81, "200_FLY_F_SCM": 119.61,
        "200_FLY_M_LCM": 110.73, "200_FLY_M_SCM": 108.24,
        "200_FREE_F_LCM": 112.98, "200_FREE_F_SCM": 110.31,
        "200_FREE_M_LCM": 102, "200_FREE_M_SCM": 99.37,
        "200_MEDLEY_F_LCM": 126.12, "200_MEDLEY_F_SCM": 121.86,
        "200_MEDLEY_M_LCM": 114, "200_MEDLEY_M_SCM": 109.63,
        "400_FREE_F_LCM": 236.46, "400_FREE_F_SCM": 233.92,
        "400_FREE_M_LCM": 220.07, "400_FREE_M_SCM": 212.25,
        "400_MEDLEY_F_LCM": 266.36, "400_MEDLEY_F_SCM": 258.94,
        "400_MEDLEY_M_LCM": 243.84, "400_MEDLEY_M_SCM": 234.81,
        "800_FREE_F_LCM": 484.79, "800_FREE_F_SCM": 479.34,
        "800_FREE_M_LCM": 452.12, "800_FREE_M_SCM": 443.42,
        "1500_FREE_F_LCM": 920.48, "1500_FREE_F_SCM": 918.01,
        "1500_FREE_M_LCM": 871.02, "1500_FREE_M_SCM": 846.88
    }
    
    @classmethod
    def calculate(
        cls, 
        time: str, 
        distance: int, 
        stroke: str, 
        gender: str, 
        course: str
    ) -> int:
        """
        Calculate FINA points for a swim time.
        
        Args:
            time: Swim time in HH:MM:SS.ss format
            distance: Distance in meters
            stroke: Stroke type (FREE, BACK, BREAST, FLY, MEDLEY)
            gender: M or F
            course: LCM or SCM
            
        Returns:
            FINA points (integer)
        """
        key = f"{distance}_{stroke}_{gender}_{course}"
        
        if key not in cls.BASE_TIMES:
            return 0
        
        base_time = cls.BASE_TIMES[key]
        time_seconds = TimeUtils.time_to_timedelta(time).total_seconds()
        
        if time_seconds <= 0:
            return 0
        
        points = 1000 * (base_time / time_seconds) ** 3
        return round(points)


class TeamCodeGenerator:
    """Generates unique team codes."""
    
    @staticmethod
    def generate(team_name: str) -> str:
        """
        Generate a unique code for a team.
        
        Args:
            team_name: Full team name
            
        Returns:
            Base64-encoded hash code
        """
        digest = hashlib.md5(team_name.encode()).digest()
        
        # XOR bytes to create 3-byte hash
        hash_bytes = bytes([
            digest[0] ^ digest[1] ^ digest[2] ^ digest[3] ^ digest[14] ^ digest[15],
            digest[4] ^ digest[5] ^ digest[6] ^ digest[7] ^ digest[13],
            digest[8] ^ digest[9] ^ digest[10] ^ digest[11] ^ digest[12]
        ])
        
        return base64.urlsafe_b64encode(hash_bytes).decode('utf-8')


class InputValidator:
    """Validates user input."""
    
    @staticmethod
    def validate_url(url: str, pattern: str) -> bool:
        """
        Validate URL against pattern.
        
        Args:
            url: URL to validate
            pattern: Regex pattern
            
        Returns:
            True if valid, False otherwise
        """
        import re
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_course(course: str) -> bool:
        """Validate pool course."""
        return course in ['SCM', 'LCM']