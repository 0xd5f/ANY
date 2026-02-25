import logging
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from dependency import get_session_manager
from session import SessionManager
import cli_api

router = APIRouter()

class AddClientRequest(BaseModel):
    name: str

@router.post('/install')
async def install_wireguard(session_manager: SessionManager = Depends(get_session_manager)):
    try:
        cli_api.install_wireguard()
        return {"detail": "WireGuard installed successfully"}
    except Exception as e:
        logging.error(f"Error installing wireguard: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/uninstall')
async def uninstall_wireguard(session_manager: SessionManager = Depends(get_session_manager)):
    try:
        cli_api.uninstall_wireguard()
        return {"detail": "WireGuard uninstalled successfully"}
    except Exception as e:
        logging.error(f"Error uninstalling wireguard: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/clients')
async def add_client(request: AddClientRequest, session_manager: SessionManager = Depends(get_session_manager)):
    try:
        if not request.name or not request.name.isalnum():
            raise HTTPException(status_code=400, detail="Invalid client name. Use alphanumeric characters only.")
            
        client = cli_api.wireguard_add_client(request.name)
        return {"detail": "Client added successfully", "client": client}
    except Exception as e:
        logging.error(f"Error adding wireguard client: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete('/clients/{client_name}')
async def remove_client(client_name: str, session_manager: SessionManager = Depends(get_session_manager)):
    try:
        cli_api.wireguard_remove_client(client_name)
        return {"detail": "Client removed successfully"}
    except Exception as e:
        logging.error(f"Error removing wireguard client: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/clients/{client_name}/config')
async def get_client_config(client_name: str, session_manager: SessionManager = Depends(get_session_manager)):
    try:
        config = cli_api.wireguard_get_client_config(client_name)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return {"config": config}
    except Exception as e:
        logging.error(f"Error getting wireguard client config: {e}")
        raise HTTPException(status_code=400, detail=str(e))
