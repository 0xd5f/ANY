from pydantic import BaseModel, field_validator
from ipaddress import ip_address
import re
from typing import Optional, List
from datetime import datetime

def validate_ip_or_domain(v: str) -> str | None:
    if v is None or v.strip() in ['', 'None']:
        return None
        
    v_stripped = v.strip()
    
    try:
        ip_address(v_stripped)
        return v_stripped
    except ValueError:
        domain_regex = re.compile(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', 
            re.IGNORECASE
        )
        if domain_regex.match(v_stripped):
            return v_stripped
        raise ValueError(f"'{v_stripped}' is not a valid IP address or domain name.")

class StatusResponse(BaseModel):
    ipv4: str | None = None
    ipv6: str | None = None

    @field_validator('ipv4', 'ipv6', mode='before')
    def check_local_server_ip(cls, v: str | None):
        return validate_ip_or_domain(v)

class EditInputBody(StatusResponse):
    pass

class Node(BaseModel):
    name: str
    ip: str
    port: Optional[int] = None
    sni: Optional[str] = None
    pinSHA256: Optional[str] = None
    obfs: Optional[str] = None
    insecure: Optional[bool] = False
    location: Optional[str] = None

    @field_validator('ip', mode='before')
    def check_node_ip(cls, v: str | None):
        if not v or not v.strip():
            raise ValueError("IP or Domain field cannot be empty.")
        return validate_ip_or_domain(v)

    @field_validator('port')
    def check_port(cls, v: int | None):
        if v is not None and not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535.')
        return v
    
    @field_validator('sni', mode='before')
    def check_sni(cls, v: str | None):
        if v is None or not v.strip():
            return None
        v = v.strip()
        try:
            ip_address(v)
            raise ValueError("SNI must be a domain name, not an IP address.")
        except ValueError:
            pass 
        if "://" in v:
            raise ValueError("SNI cannot contain '://'")
        domain_regex = re.compile(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', 
            re.IGNORECASE
        )
        if not domain_regex.match(v):
            raise ValueError("Invalid domain name format for SNI.")
        return v
    
    @field_validator('pinSHA256', mode='before')
    def check_pin(cls, v: str | None):
        if v is None or not v.strip():
            return None
        v_stripped = v.strip().upper()
        pin_regex = re.compile(r'^([0-9A-F]{2}:){31}[0-9A-F]{2}$')
        if not pin_regex.match(v_stripped):
            raise ValueError("Invalid SHA256 pin format.")
        return v_stripped

class AddNodeBody(Node):
    pass

class EditNodeBody(BaseModel):
    name: str
    new_name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    sni: Optional[str] = None
    pinSHA256: Optional[str] = None
    obfs: Optional[str] = None
    insecure: Optional[bool] = None
    location: Optional[str] = None

    @field_validator('ip', mode='before')
    def check_node_ip(cls, v: str | None):
        if v is None: return None
        if not v.strip(): return None
        return validate_ip_or_domain(v)

    @field_validator('port')
    def check_port(cls, v: int | None):
        if v is not None and not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535.')
        return v
    
    @field_validator('sni', mode='before')
    def check_sni(cls, v: str | None):
        if v is None: return None
        if not v.strip(): return ""
        v = v.strip()
        try:
            ip_address(v)
            raise ValueError("SNI must be a domain name, not an IP address.")
        except ValueError:
            pass 
        if "://" in v:
            raise ValueError("SNI cannot contain '://'")
        domain_regex = re.compile(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', 
            re.IGNORECASE
        )
        if not domain_regex.match(v):
            raise ValueError("Invalid domain name format for SNI.")
        return v
    
    @field_validator('pinSHA256', mode='before')
    def check_pin(cls, v: str | None):
        if v is None: return None
        if not v.strip(): return ""
        v_stripped = v.strip().upper()
        pin_regex = re.compile(r'^([0-9A-F]{2}:){31}[0-9A-F]{2}$')
        if not pin_regex.match(v_stripped):
            raise ValueError("Invalid SHA256 pin format.")
        return v_stripped

class DeleteNodeBody(BaseModel):
    name: str

NodeListResponse = list[Node]

class NodeUserTraffic(BaseModel):
    username: str
    upload_bytes: int
    download_bytes: int
    status: str
    online_count: int
    account_creation_date: Optional[str] = None

    @field_validator('account_creation_date')
    def check_date_format(cls, v: str | None):
        if v is None:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("account_creation_date must be in YYYY-MM-DD format.")

class NodesTrafficPayload(BaseModel):
    users: List[NodeUserTraffic]

class NodeHeartbeatBody(BaseModel):
    node_name: str
    cpu_percent: float
    ram_percent: float
    ram_used: float
    ram_total: float
    uptime: str
    hysteria_active: bool

class RestartNodeBody(BaseModel):
    node_name: str