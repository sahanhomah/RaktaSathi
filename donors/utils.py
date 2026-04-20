import math


BLOOD_GROUP_ORDER = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']

BLOOD_COMPATIBILITY = {
    'O-': {'O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'},
    'O+': {'O+', 'A+', 'B+', 'AB+'},
    'A-': {'A-', 'A+', 'AB-', 'AB+'},
    'A+': {'A+', 'AB+'},
    'B-': {'B-', 'B+', 'AB-', 'AB+'},
    'B+': {'B+', 'AB+'},
    'AB-': {'AB-', 'AB+'},
    'AB+': {'AB+'},
}


def can_donate_to(donor_group: str, recipient_group: str) -> bool:
    return recipient_group in BLOOD_COMPATIBILITY.get(donor_group, set())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the distance in kilometers between two lat/lon points."""
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def normalize_nepali_phone(value: str) -> str | None:
    """Normalize Nepali mobile formats to +97798XXXXXXXX; return None if invalid."""
    raw = (value or '').strip()
    normalized = ''.join(char for char in raw if char.isdigit() or char == '+')

    if normalized.startswith('+977'):
        local_number = normalized[4:]
        if len(local_number) == 10 and local_number.startswith('9'):
            return normalized

    if normalized.startswith('977'):
        local_number = normalized[3:]
        if len(local_number) == 10 and local_number.startswith('9'):
            return f'+{normalized}'

    if normalized.startswith('0') and len(normalized) == 11 and normalized[1] == '9':
        return f'+977{normalized[1:]}'

    if len(normalized) == 10 and normalized.startswith('9'):
        return f'+977{normalized}'

    return None
