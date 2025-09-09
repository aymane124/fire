import re
from typing import Tuple, Optional

def dms_to_decimal(dms: str) -> Optional[float]:
    """Convertit les coordonnées DMS en décimal."""
    try:
        # Format: 33°34'43.0"N ou 33°34'43.0"S
        match = re.match(r'(\d+)°(\d+)\'([\d.]+)"([NSEW])', dms)
        if not match:
            return None

        degrees, minutes, seconds, direction = match.groups()
        decimal = float(degrees) + float(minutes)/60 + float(seconds)/3600
        
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal
    except:
        return None

def parse_coordinates(location: str) -> Optional[Tuple[float, float]]:
    """Parse les coordonnées depuis différents formats."""
    if not location:
        return None

    try:
        # Format DMS: "33°34'43.0"N 7°40'35.8"W"
        if '°' in location:
            parts = location.split()
            if len(parts) != 2:
                return None
            lat = dms_to_decimal(parts[0])
            lng = dms_to_decimal(parts[1])
            if lat is not None and lng is not None:
                return (lat, lng)

        # Format décimal: "33.5786, -7.6766" ou "33.5786 -7.6766"
        coords = re.split(r'[, \t]+', location.strip())
        if len(coords) == 2:
            lat = float(coords[0])
            lng = float(coords[1])
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return (lat, lng)

        return None
    except:
        return None

def format_location(lat: float, lng: float, format: str = 'decimal') -> str:
    """Formate les coordonnées dans le format spécifié."""
    if format == 'decimal':
        return f"{lat:.6f}, {lng:.6f}"
    elif format == 'dms':
        lat_dms = decimal_to_dms(lat, True)
        lng_dms = decimal_to_dms(lng, False)
        return f"{lat_dms} {lng_dms}"
    return f"{lat:.6f}, {lng:.6f}"

def decimal_to_dms(decimal: float, is_latitude: bool) -> str:
    """Convertit les coordonnées décimales en DMS."""
    direction = 'N' if is_latitude and decimal >= 0 else 'S' if is_latitude else 'E' if decimal >= 0 else 'W'
    decimal = abs(decimal)
    degrees = int(decimal)
    minutes = int((decimal - degrees) * 60)
    seconds = round((decimal - degrees - minutes/60) * 3600, 1)
    return f"{degrees}°{minutes}'{seconds}\"{direction}" 