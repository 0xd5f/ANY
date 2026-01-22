from pydantic import BaseModel, Field
from typing import Optional

class StartInputBody(BaseModel):
    domain: str
    port: int

class EditProfileTitleInputBody(BaseModel):
    title: str = Field(..., min_length=1, description="The new profile title.")

class GetProfileTitleResponse(BaseModel):
    title: str = Field(..., description="The current NormalSub profile title.")

class EditSupportUrlInputBody(BaseModel):
    url: str = Field("", description="The new support URL (can be empty).")

class GetSupportUrlResponse(BaseModel):
    url: str = Field(..., description="The current NormalSub support URL.")

class EditShowUsernameInputBody(BaseModel):
    enabled: bool = Field(..., description="Whether to show username in subscription profile title.")

class GetShowUsernameResponse(BaseModel):
    enabled: bool = Field(..., description="Current status of show username setting.")

class EditSubPathInputBody(BaseModel):
    subpath: str = Field(..., min_length=1, pattern=r"^[a-zA-Z0-9]+(?:/[a-zA-Z0-9]+)*$", description="The new subpath, must be alphanumeric.")

class GetSubPathResponse(BaseModel):
    subpath: Optional[str] = Field(None, description="The current NormalSub subpath, or null if not set/found.")