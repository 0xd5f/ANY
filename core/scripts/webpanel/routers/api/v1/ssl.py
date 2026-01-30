from fastapi import APIRouter, File, UploadFile, HTTPException, Body
from pydantic import BaseModel
import shutil
import subprocess
import os

router = APIRouter()

HYSTERIA_DIR = "/etc/hysteria"
WEBPANEL_SHELL = f"{HYSTERIA_DIR}/core/scripts/webpanel/webpanel_shell.sh"

class SSLToggleRequest(BaseModel):
    self_signed: bool

class SSLPathsRequest(BaseModel):
    cert_path: str
    key_path: str

@router.post("/paths")
async def set_ssl_paths(data: SSLPathsRequest):
    if not os.path.exists(data.cert_path):
        raise HTTPException(status_code=400, detail=f"Certificate file not found: {data.cert_path}")
    if not os.path.exists(data.key_path):
        raise HTTPException(status_code=400, detail=f"Key file not found: {data.key_path}")
        
    try:
        subprocess.run(["bash", WEBPANEL_SHELL, "ssl_paths", data.cert_path, data.key_path], check=True)
        return {"status": "success", "message": "Custom SSL paths updated successfully."}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail="Failed to apply SSL paths.")

@router.post("/upload")
async def upload_ssl_cert(
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...)
):
    try:
        # Save files to /etc/hysteria/server.crt and server.key
        cert_path = os.path.join(HYSTERIA_DIR, "server.crt")
        key_path = os.path.join(HYSTERIA_DIR, "server.key")

        with open(cert_path, "wb") as buffer:
            shutil.copyfileobj(cert_file.file, buffer)
            
        with open(key_path, "wb") as buffer:
            shutil.copyfileobj(key_file.file, buffer)

        # Apply changes (Toggle SELF_SIGNED=false via shell script)
        # We assume if user uploads certs, they want to use them.
        subprocess.run(["bash", WEBPANEL_SHELL, "ssl", "false"], check=True)

        return {"status": "success", "message": "Certificates uploaded and applied successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/toggle")
async def toggle_ssl_mode(data: SSLToggleRequest):
    mode = "true" if data.self_signed else "false"
    try:
        subprocess.run(["bash", WEBPANEL_SHELL, "ssl", mode], check=True)
        return {"status": "success", "message": f"SSL mode set to {'Self-Signed' if data.self_signed else 'Custom'}."}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail="Failed to apply SSL settings.")
