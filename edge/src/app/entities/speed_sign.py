from pydantic import BaseModel


class SpeedSign(BaseModel):
    sign_id: str
    speed_limit: int
    location: list[float]
