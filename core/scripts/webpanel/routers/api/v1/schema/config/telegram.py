from pydantic import BaseModel
from typing import Optional


class StartInputBody(BaseModel):
    token: str
    admin_id: str
    backup_interval: Optional[int] = None


class SetIntervalInputBody(BaseModel):
    backup_interval: int


class BackupIntervalResponse(BaseModel):
    backup_interval: Optional[int] = None


class TelegramBotInfoResponse(BaseModel):
    id: Optional[int] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    can_join_groups: Optional[bool] = None
    can_read_all_group_messages: Optional[bool] = None
    supports_inline_queries: Optional[bool] = None
    error: Optional[str] = None