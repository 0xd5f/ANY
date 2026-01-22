import re
from typing import Optional, List
from pydantic import BaseModel, RootModel, Field, field_validator


class UserInfoResponse(BaseModel):
    username: str
    password: str
    max_download_bytes: int
    expiration_days: int
    account_creation_date: Optional[str] = None
    blocked: bool
    unlimited_ip: bool = Field(False, alias='unlimited_user')
    note: Optional[str] = None
    status: Optional[str] = None
    upload_bytes: Optional[int] = None
    download_bytes: Optional[int] = None
    online_count: int = 0


class UserListResponse(RootModel):
    root: List[UserInfoResponse]

class UsernamesRequest(BaseModel):
    usernames: List[str]

class AddUserInputBody(BaseModel):
    username: str
    traffic_limit: int
    expiration_days: int
    password: Optional[str] = None
    creation_date: Optional[str] = None
    unlimited: bool = False
    note: Optional[str] = None

    @field_validator('username')
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError('Username can only contain letters, numbers, and underscores.')
        return v


class AddBulkUsersInputBody(BaseModel):
    traffic_gb: float
    expiration_days: int
    count: int
    prefix: str
    start_number: int = 1
    unlimited: bool = False

    @field_validator('prefix')
    def validate_prefix(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]*$", v):
            raise ValueError('Prefix can only contain letters, numbers, and underscores.')
        return v


class EditUserInputBody(BaseModel):
    new_username: Optional[str] = Field(None, description="The new username for the user.")
    new_password: Optional[str] = Field(None, description="The new password for the user. Leave empty to keep the current one.")
    new_traffic_limit: Optional[int] = Field(None, description="The new traffic limit in GB.")
    new_expiration_days: Optional[int] = Field(None, description="The new expiration in days.")
    renew_password: bool = Field(False, description="Whether to renew the user's password. Used by legacy clients like the bot.")
    renew_creation_date: bool = Field(False, description="Whether to renew the user's account creation date.")
    blocked: Optional[bool] = Field(None, description="Whether the user is blocked.")
    unlimited_ip: Optional[bool] = Field(None, description="Whether the user has unlimited IP access.")
    note: Optional[str] = Field(None, description="A note for the user.")

    @field_validator('new_username')
    def validate_new_username(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError('Username can only contain letters, numbers, and underscores.')
        return v

class NodeUri(BaseModel):
    name: str
    uri: str

class UserUriResponse(BaseModel):
    username: str
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    nodes: Optional[List[NodeUri]] = []
    normal_sub: Optional[str] = None
    error: Optional[str] = None