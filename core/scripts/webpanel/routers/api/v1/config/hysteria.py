from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from ..schema.config.hysteria import ConfigFile, GetPortResponse, GetSniResponse, GetObfsResponse, GetMasqueradeStatusResponse
from ..schema.response import DetailResponse, IPLimitConfig, SetupDecoyRequest, DecoyStatusResponse, IPLimitConfigResponse
from fastapi.responses import FileResponse
import shutil
import zipfile
import tempfile
import os
from pathlib import Path
import cli_api

router = APIRouter()

@router.patch('/update', response_model=DetailResponse, summary='Update Hysteria2')
async def update():
    try:
        cli_api.update_hysteria2()
        return DetailResponse(detail='Hysteria2 updated successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.post('/restart', response_model=DetailResponse, summary='Restart Hysteria2 Service')
async def restart_service():
    try:
        cli_api.restart_hysteria2()
        return DetailResponse(detail='Hysteria2 service restarted successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/get-port', response_model=GetPortResponse, summary='Get Hysteria2 port')
async def get_port_api():
    try:
        if port := cli_api.get_hysteria2_port():
            return GetPortResponse(port=port)
        else:
            raise HTTPException(status_code=404, detail='Hysteria2 port not found.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/set-port/{port}', response_model=DetailResponse, summary='Set Hysteria2 port')
async def set_port_api(port: int):
    try:
        cli_api.change_hysteria2_port(port)
        return DetailResponse(detail=f'Hysteria2 port changed to {port} successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/get-sni', response_model=GetSniResponse, summary='Get Hysteria2 SNI')
async def get_sni_api():
    try:
        if sni := cli_api.get_hysteria2_sni():
            return GetSniResponse(sni=sni)
        else:
            raise HTTPException(status_code=404, detail='Hysteria2 SNI not found.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/set-sni/{sni}', response_model=DetailResponse, summary='Set Hysteria2 SNI')
async def set_sni_api(sni: str):
    try:
        cli_api.change_hysteria2_sni(sni)
        return DetailResponse(detail=f'Hysteria2 SNI changed to {sni} successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/backup', response_class=FileResponse, summary='Backup Hysteria2 configuration')
async def backup_api():
    try:
        cli_api.backup_hysteria2()
        backup_dir = "/opt/hysbackup/"

        if not os.path.isdir(backup_dir):
            raise HTTPException(status_code=500, detail="Backup directory does not exist.")

        files = [f for f in os.listdir(backup_dir) if f.endswith('.zip')]
        files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)), reverse=True)
        latest_backup_file = files[0] if files else None

        if latest_backup_file:
            backup_file_path = os.path.join(backup_dir, latest_backup_file)
            if not os.path.exists(backup_file_path):
                raise HTTPException(status_code=404, detail="Backup file not found.")
            return FileResponse(path=backup_file_path, filename=os.path.basename(backup_file_path), media_type="application/zip")
        else:
            raise HTTPException(status_code=500, detail="No backup file found after backup process.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')


@router.post('/restore', response_model=DetailResponse, summary='Restore Hysteria2 Configuration')
async def restore_api(file: UploadFile = File(...)):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        if not zipfile.is_zipfile(temp_path):
            raise HTTPException(status_code=400, detail="Invalid file type. Must be a ZIP file.")

        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
            namelist = zip_ref.namelist()
            
            required_flat_files = {"ca.key", "ca.crt", "config.json", ".configs.env"}
            missing_files = required_flat_files - set(namelist)
            if missing_files:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Backup is missing required configuration files: {', '.join(missing_files)}"
                )

            db_dump_prefix = "blitz_panel/"
            if not any(name.startswith(db_dump_prefix) for name in namelist):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Backup file is not a modern backup and is missing the database dump directory: '{db_dump_prefix}'"
                )

        cli_api.restore_hysteria2(temp_path)
        return DetailResponse(detail='Hysteria2 restored successfully.')

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@router.get('/enable-obfs', response_model=DetailResponse, summary='Enable Hysteria2 obfs')
async def enable_obfs():
    try:
        cli_api.enable_hysteria2_obfs()
        return DetailResponse(detail='Hysteria2 obfs enabled successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/disable-obfs', response_model=DetailResponse, summary='Disable Hysteria2 obfs')
async def disable_obfs():
    try:
        cli_api.disable_hysteria2_obfs()
        return DetailResponse(detail='Hysteria2 obfs disabled successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/check-obfs', response_model=GetObfsResponse, summary='Check Hysteria2 OBFS Status')
async def check_obfs():
    try:
        obfs_status_message = cli_api.check_hysteria2_obfs()
        return GetObfsResponse(obfs=obfs_status_message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error checking OBFS status: {str(e)}')

@router.get('/enable-masquerade', response_model=DetailResponse, summary='Enable Hysteria2 masquerade')
async def enable_masquerade():
    try:
        response = cli_api.enable_hysteria2_masquerade()
        return DetailResponse(detail=response)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/disable-masquerade', response_model=DetailResponse, summary='Disable Hysteria2 masquerade')
async def disable_masquerade():
    try:
        cli_api.disable_hysteria2_masquerade()
        return DetailResponse(detail='Hysteria2 masquerade disabled successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.get('/check-masquerade', response_model=GetMasqueradeStatusResponse, summary='Check Hysteria2 Masquerade Status')
async def check_masquerade():
    try:
        status_message = cli_api.get_hysteria2_masquerade_status()
        return GetMasqueradeStatusResponse(status=status_message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error checking Masquerade status: {str(e)}')

@router.get('/file', response_model=ConfigFile, summary='Get Hysteria2 configuration file')
async def get_file():
    try:
        if config_file := cli_api.get_hysteria2_config_file():
            return ConfigFile(root=config_file)
        else:
            raise HTTPException(status_code=404, detail='Hysteria2 configuration file not found.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.post('/file', response_model=DetailResponse, summary='Update Hysteria2 configuration file')
async def set_file(body: ConfigFile):
    try:
        cli_api.set_hysteria2_config_file(body.root)
        cli_api.restart_hysteria2()
        return DetailResponse(detail='Hysteria2 configuration file updated successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')

@router.post('/ip-limit/start', response_model=DetailResponse, summary='Start IP Limiter Service')
async def start_ip_limit_api():
    try:
        cli_api.start_ip_limiter()
        return DetailResponse(detail='IP Limiter service started successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error starting IP Limiter: {str(e)}')

@router.post('/ip-limit/stop', response_model=DetailResponse, summary='Stop IP Limiter Service')
async def stop_ip_limit_api():
    try:
        cli_api.stop_ip_limiter()
        return DetailResponse(detail='IP Limiter service stopped successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error stopping IP Limiter: {str(e)}')

@router.post('/ip-limit/clean', response_model=DetailResponse, summary='Clean IP Limiter Database')
async def clean_ip_limit_api():
    try:
        cli_api.clean_ip_limiter()
        return DetailResponse(detail='IP Limiter database and block list have been cleaned successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error cleaning IP Limiter: {str(e)}')

@router.post('/ip-limit/config', response_model=DetailResponse, summary='Configure IP Limiter')
async def config_ip_limit_api(config: IPLimitConfig):
    try:
        cli_api.config_ip_limiter(config.block_duration, config.max_ips)
        details = 'IP Limiter configuration updated successfully.'
        if config.block_duration is not None:
            details += f' Block Duration: {config.block_duration} seconds.'
        if config.max_ips is not None:
            details += f' Max IPs per user: {config.max_ips}.'
        return DetailResponse(detail=details)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error configuring IP Limiter: {str(e)}')

@router.get('/ip-limit/config', response_model=IPLimitConfigResponse, summary='Get IP Limiter Configuration')
async def get_ip_limit_config_api():
    try:
        config = cli_api.get_ip_limiter_config()
        return IPLimitConfigResponse(**config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error retrieving IP Limiter configuration: {str(e)}')

def run_setup_decoy_background(domain: str, decoy_path: str):
    try:
        cli_api.setup_webpanel_decoy(domain, decoy_path)
    except Exception:
        pass

def run_stop_decoy_background():
    try:
        cli_api.stop_webpanel_decoy()
    except Exception:
        pass 

@router.post('/webpanel/decoy/setup', response_model=DetailResponse, summary='Setup/Update WebPanel Decoy Site (Background Task)')
async def setup_decoy_api(request_body: SetupDecoyRequest, background_tasks: BackgroundTasks):
    if not os.path.isdir(request_body.decoy_path):
         raise HTTPException(status_code=400, detail=f"Decoy path does not exist or is not a directory: {request_body.decoy_path}")

    background_tasks.add_task(run_setup_decoy_background, request_body.domain, request_body.decoy_path)

    return DetailResponse(detail=f'Web Panel decoy site setup initiated for domain {request_body.domain}. Caddy will restart in the background.')


@router.post('/webpanel/decoy/stop', response_model=DetailResponse, summary='Stop WebPanel Decoy Site (Background Task)')
async def stop_decoy_api(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_stop_decoy_background)

    return DetailResponse(detail='Web Panel decoy site stop initiated. Caddy will restart in the background.')

@router.get('/webpanel/decoy/status', response_model=DecoyStatusResponse, summary='Get WebPanel Decoy Site Status')
async def get_decoy_status_api():
    try:
        status = cli_api.get_webpanel_decoy_status()
        return DecoyStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error retrieving decoy status: {str(e)}')