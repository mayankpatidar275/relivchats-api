from pydantic import BaseModel
from datetime import datetime

class UserStore(BaseModel):
    user_id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None

class UserOut(BaseModel):
    user_id: str
    email: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class UserDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_at: datetime
    user_id: str