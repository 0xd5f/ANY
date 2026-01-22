from fastapi import APIRouter, HTTPException
import cli_api
from .schema.server import ServerStatusResponse, ServerServicesStatusResponse, VersionCheckResponse, VersionInfoResponse

router = APIRouter()


@router.get('/status', response_model=ServerStatusResponse)
async def server_status_api():

    try:
        if res := cli_api.server_info():
            return __parse_server_status(res)
        raise HTTPException(status_code=404, detail='Server information not available.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


def __parse_server_status(server_info: str) -> ServerStatusResponse:
    data = {
        'uptime': 'N/A',
        'boot_time': 'N/A',
        'server_ipv4': 'N/A',
        'server_ipv6': 'N/A',
        'cpu_usage': '0%',
        'total_ram': '0MB',
        'ram_usage': '0MB',
        'online_users': 0,
        'upload_speed': '0 B/s',
        'download_speed': '0 B/s',
        'tcp_connections': 0,
        'udp_connections': 0,
        'reboot_uploaded_traffic': '0 B',
        'reboot_downloaded_traffic': '0 B',
        'reboot_total_traffic': '0 B',
        'user_uploaded_traffic': '0 B',
        'user_downloaded_traffic': '0 B',
        'user_total_traffic': '0 B'
    }

    current_section = 'general'

    for line in server_info.splitlines():
        line = line.strip()
        if not line:
            continue

        if 'Traffic Since Last Reboot' in line:
            current_section = 'reboot'
            continue
        elif 'User Traffic (All Time)' in line:
            current_section = 'user'
            continue
            
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if not key or not value:
            continue
        
        try:
            if 'uptime' in key:
                uptime_part, _, boottime_part = value.partition('(')
                data['uptime'] = uptime_part.strip()
                data['boot_time'] = boottime_part.replace('since ', '').replace(')', '').strip()
            elif 'server ipv4' in key:
                data['server_ipv4'] = value
            elif 'server ipv6' in key:
                data['server_ipv6'] = value
            elif 'cpu usage' in key:
                data['cpu_usage'] = value
            elif 'used ram' in key:
                parts = value.split('/')
                if len(parts) == 2:
                    data['ram_usage'] = parts[0].strip()
                    data['total_ram'] = parts[1].strip()
            elif 'online users' in key:
                data['online_users'] = int(value)
            elif 'upload speed' in key:
                data['upload_speed'] = value
            elif 'download speed' in key:
                data['download_speed'] = value
            elif 'tcp connections' in key:
                data['tcp_connections'] = int(value)
            elif 'udp connections' in key:
                data['udp_connections'] = int(value)
            elif 'total uploaded' in key or 'uploaded traffic' in key:
                if current_section == 'reboot':
                    data['reboot_uploaded_traffic'] = value
                elif current_section == 'user':
                    data['user_uploaded_traffic'] = value
            elif 'total downloaded' in key or 'downloaded traffic' in key:
                if current_section == 'reboot':
                    data['reboot_downloaded_traffic'] = value
                elif current_section == 'user':
                    data['user_downloaded_traffic'] = value
            elif 'combined traffic' in key or 'total traffic' in key:
                if current_section == 'reboot':
                    data['reboot_total_traffic'] = value
                elif current_section == 'user':
                    data['user_total_traffic'] = value
        except (ValueError, IndexError) as e:
            raise ValueError(f'Error parsing line \'{line}\': {e}')

    try:
        return ServerStatusResponse(**data)
    except Exception as e:
        raise ValueError(f'Invalid or incomplete server info: {e}')


@router.get('/services/status', response_model=ServerServicesStatusResponse)
async def server_services_status_api():

    try:
        if res := cli_api.get_services_status():
            return __parse_services_status(res)
        raise HTTPException(status_code=404, detail='Services status not available.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


def __parse_services_status(services_status: dict[str, bool]) -> ServerServicesStatusResponse:
    parsed_services_status: dict[str, bool] = {}
    for service, status in services_status.items():
        if 'hysteria-server' in service:
            parsed_services_status['hysteria_server'] = status
        elif 'hysteria-ip-limit' in service:
            parsed_services_status['hysteria_iplimit'] = status
        elif 'hysteria-webpanel' in service:
            parsed_services_status['hysteria_webpanel'] = status
        elif 'telegram-bot' in service:
            parsed_services_status['hysteria_telegram_bot'] = status
        elif 'hysteria-normal-sub' in service:
            parsed_services_status['hysteria_normal_sub'] = status
        elif 'wg-quick' in service:
            parsed_services_status['hysteria_warp'] = status
    return ServerServicesStatusResponse(**parsed_services_status)

@router.get('/version', response_model=VersionInfoResponse)
async def get_version_info():
    try:
        version_output = cli_api.show_version()
        if not version_output:
            raise HTTPException(status_code=404, detail="Version information not found")

        lines = version_output.strip().splitlines()
        current_version = None
        core_version = None

        for line in lines:
            if "Panel Version:" in line:
                current_version = line.split(": ")[1].strip()
            elif "Hysteria2 Core Version:" in line:
                core_version = line.split(": ")[1].strip()

        if current_version:
            return VersionInfoResponse(current_version=current_version, core_version=core_version)
        
        raise HTTPException(status_code=404, detail="Panel version not found in output")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/version/check', response_model=VersionCheckResponse)
async def check_version_info():
    try:
        check_output = cli_api.check_version()
        if check_output:
            lines = check_output.splitlines()
            current_version = lines[0].split(": ")[1].strip()

            if len(lines) > 1 and "Latest Version" in lines[1]:
                latest_version = lines[1].split(": ")[1].strip()
                is_latest = current_version == latest_version
                changelog_start_index = 3 
                changelog = "\n".join(lines[changelog_start_index:]).strip()
                return VersionCheckResponse(is_latest=is_latest, current_version=current_version,
                                             latest_version=latest_version, changelog=changelog)
            else:
                return VersionCheckResponse(
                    is_latest=True,
                    current_version=current_version,
                    latest_version=current_version,
                    changelog="Panel is up-to-date."
                )

        raise HTTPException(status_code=404, detail="Version information not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))