import math

from app.entities.agent_data import AgentData
from app.entities.processed_agent_data import ProcessedAgentData
from app.entities.speed_sign import SpeedSign
from app.entities.violation_event import ViolationEvent

GPS_SPEED_TOLERANCE_KMH = 5


def process_agent_data(
    agent_data: AgentData,
) -> ProcessedAgentData:
    """
    Process agent data and classify the state of the road surface.
    Parameters:
        agent_data (AgentData): Agent data that contains accelerometer, GPS, and timestamp.
    Returns:
        processed_data (ProcessedAgentData): Processed data containing the classified
        state of the road surface and agent data.
    """
    z = agent_data.accelerometer.z
    y = agent_data.accelerometer.y

    if abs(y) > 300 or z < 16000:
        road_state = "pothole"
    elif abs(y) > 150 or z < 16400:
        road_state = "bumpy"
    else:
        road_state = "smooth"

    return ProcessedAgentData(
        road_state=road_state,
        agent_data=agent_data,
    )


def detect_speeding_with_signs(
    speed_kmh: float,
    speed_signs: list[SpeedSign],
    latitude: float,
    longitude: float,
    vehicle_id: str,
    timestamp,
) -> ViolationEvent | None:
    if not speed_signs or speed_kmh <= 0:
        return None

    nearest_sign: SpeedSign | None = None
    nearest_distance = math.inf

    for sign in speed_signs:
        sign_lat, sign_lon = sign.location
        dist = _haversine_m(latitude, longitude, sign_lat, sign_lon)
        if dist < nearest_distance:
            nearest_distance = dist
            nearest_sign = sign

    if nearest_sign is None:
        return None

    effective_speed = speed_kmh - GPS_SPEED_TOLERANCE_KMH
    excess = effective_speed - nearest_sign.speed_limit

    if excess <= 0:
        return None

    if excess <= 20:
        fine_type = "minor"
        fine_amount = 340
    elif excess <= 40:
        fine_type = "major"
        fine_amount = 850
    else:
        fine_type = "severe"
        fine_amount = 3400

    return ViolationEvent(
        violation_type="speeding",
        severity=fine_type,
        vehicle_id=vehicle_id,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        message=(
            f"Зафіксовано перевищення швидкості: {speed_kmh:.0f} км/год "
            f"при дозволених {nearest_sign.speed_limit} км/год "
            f"за знаком {nearest_sign.sign_id}. "
            f"Будь ласка, зменшіть швидкість."
        ),
        fine_type=fine_type,
        fine_amount=fine_amount,
        details={
            "actual_speed": round(speed_kmh, 1),
            "speed_limit": nearest_sign.speed_limit,
            "nearest_sign_id": nearest_sign.sign_id,
            "distance_to_sign_m": round(nearest_distance, 1),
        },
    )


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
