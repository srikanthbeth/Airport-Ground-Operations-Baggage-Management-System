from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.constants import BoardingPassStatus


class BoardingPassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    checkin_id: UUID
    boarding_pass_number: str
    status: BoardingPassStatus
    issued_at: datetime