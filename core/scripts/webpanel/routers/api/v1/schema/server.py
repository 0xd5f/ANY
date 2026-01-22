from pydantic import BaseModel
from typing import Optional


class ServerStatusResponse(BaseModel):
    uptime: str
    boot_time: str
    server_ipv4: str
    server_ipv6: str
    cpu_usage: str
    ram_usage: str
    total_ram: str
    online_users: int

    upload_speed: str
    download_speed: str
    tcp_connections: int
    udp_connections: int

    reboot_uploaded_traffic: str
    reboot_downloaded_traffic: str
    reboot_total_traffic: str

    user_uploaded_traffic: str
    user_downloaded_traffic: str
    user_total_traffic: str


class ServerServicesStatusResponse(BaseModel):
    hysteria_server: bool
    hysteria_webpanel: bool
    hysteria_iplimit: bool
    hysteria_normal_sub: bool
    hysteria_telegram_bot: bool
    hysteria_warp: bool

class VersionInfoResponse(BaseModel):
    current_version: str
    core_version: Optional[str] = None


class VersionCheckResponse(BaseModel):
    is_latest: bool
    current_version: str
    latest_version: str
    changelog: str