from pydantic import BaseModel, field_validator, Field
from typing import Optional

VALID_PROTOCOLS = ("vmess://", "vless://", "ss://", "trojan://")

class ExtraConfigBase(BaseModel):
    name: str = Field(..., min_length=1, description="A unique name for the configuration.")
    uri: str = Field(..., description="The proxy URI.")

    @field_validator('uri')
    def validate_uri_protocol(cls, v):
        if not any(v.startswith(protocol) for protocol in VALID_PROTOCOLS):
            raise ValueError(f"Invalid URI. Must start with one of {', '.join(VALID_PROTOCOLS)}")
        return v

class AddExtraConfigBody(ExtraConfigBase):
    pass

class EditExtraConfigBody(BaseModel):
    name: str = Field(..., description="The original name of the config to edit.")
    new_name: str = Field(None, min_length=1, description="The new name.")
    uri: str = Field(None, description="The new URI.")
    enabled: Optional[bool] = Field(None, description="Enable or disable the configuration.")

    @field_validator('uri')
    def validate_uri_protocol(cls, v):
        if v and not any(v.startswith(protocol) for protocol in VALID_PROTOCOLS):
            raise ValueError(f"Invalid URI. Must start with one of {', '.join(VALID_PROTOCOLS)}")
        return v

class DeleteExtraConfigBody(BaseModel):
    name: str

class ExtraConfigResponse(ExtraConfigBase):
    pass

ExtraConfigListResponse = list[ExtraConfigResponse]