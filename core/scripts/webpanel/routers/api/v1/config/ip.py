from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from ..schema.response import DetailResponse
import json
import os
from scripts.db.database import db

from ..schema.config.ip import (
    EditInputBody, 
    StatusResponse,
    AddNodeBody,
    EditNodeBody,
    DeleteNodeBody,
    NodeListResponse,
    NodesTrafficPayload,
    NodeHeartbeatBody,
    RestartNodeBody,
    AutoInstallNodeBody,
    TunnelExecBody
)
import cli_api
import time
import socket
import asyncio
from config.config import CONFIGS

router = APIRouter()

NODE_STATUS_STORE = {}
NODE_COMMAND_QUEUE = {}

def check_tcp_port(host, port, timeout=3):
    try:
        addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        
        for family, type, proto, canonname, sockaddr in addr_info:
            try:
                s = socket.socket(family, type, proto)
                s.settimeout(timeout)
                s.connect(sockaddr)
                s.close()
                return True
            except Exception:
                pass
        return False
    except (socket.timeout, ConnectionRefusedError, OSError, ValueError, TypeError):
        return False

@router.get('/get', response_model=StatusResponse, summary='Get Local Server IP Status')
async def get_ip_api():
    try:

        ipv4, ipv6, server_name = cli_api.get_ip_address()
        return StatusResponse(ipv4=ipv4, ipv6=ipv6, server_name=server_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/add', response_model=DetailResponse, summary='Detect and Add Local Server IP')
async def add_ip_api():
    try:
        cli_api.add_ip_address()
        return DetailResponse(detail='IP addresses added successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.post('/edit', response_model=DetailResponse, summary='Edit Local Server IP')
async def edit_ip_api(body: EditInputBody):
    try:
        server_name_val = str(body.server_name) if body.server_name is not None else None
        cli_api.edit_ip_address(str(body.ipv4), str(body.ipv6), server_name_val)
        return DetailResponse(detail='IP address edited successfully.')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error: {str(e)}')


@router.get('/main-config', summary='Get Main Server Config for Tunneling')
async def get_main_config():
    ipv4, ipv6, server_name = cli_api.get_ip_address()
    target_ip = ipv4 if ipv4 else ipv6
    
    port = "443"
    try:
        if os.path.exists(cli_api.CONFIG_FILE):
             with open(cli_api.CONFIG_FILE, 'r') as f:
                data = json.load(f)
                listen = data.get("listen", ":443")
                if ":" in listen:
                    port = listen.split(":")[-1]
    except:
        pass

    return {
        "ip": target_ip,
        "port": int(port) if port.isdigit() else 443
    }


@router.get('/nodes', response_model=NodeListResponse, summary='Get All External Nodes')
async def get_all_nodes():
    if not os.path.exists(cli_api.NODES_JSON_PATH):
        return []
    try:
        with open(cli_api.NODES_JSON_PATH, 'r') as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read or parse nodes file: {e}")


@router.post('/nodes/add', response_model=DetailResponse, summary='Add External Node')
async def add_node(body: AddNodeBody):
    try:
        cli_api.add_node(
            name=body.name, 
            ip=body.ip, 
            port=body.port, 
            sni=body.sni, 
            pinSHA256=body.pinSHA256, 
            obfs=body.obfs,
            insecure=body.insecure,
            location=body.location
        )
        return DetailResponse(detail=f"Node '{body.name}' added successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/nodes/edit', response_model=DetailResponse, summary='Edit External Node')
async def edit_node(body: EditNodeBody):
    try:
        cli_api.edit_node(
            name=body.name,
            new_name=body.new_name,
            ip=body.ip,
            port=body.port,
            sni=body.sni,
            pinSHA256=body.pinSHA256,
            obfs=body.obfs,
            insecure=body.insecure,
            location=body.location
        )
        return DetailResponse(detail=f"Node '{body.new_name if body.new_name else body.name}' edited successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/nodes/delete', response_model=DetailResponse, summary='Delete External Node')
async def delete_node(body: DeleteNodeBody):
    try:
        cli_api.delete_node(body.name)
        return DetailResponse(detail=f"Node '{body.name}' deleted successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/nodestraffic', response_model=DetailResponse, summary='Receive and Aggregate Traffic from Node')
async def receive_node_traffic(body: NodesTrafficPayload):
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection is not available.")
    
    updated_count = 0
    for user_traffic in body.users:
        try:
            db_user = db.get_user(user_traffic.username)
            if not db_user:
                continue

            new_upload = db_user.get('upload_bytes', 0) + user_traffic.upload_bytes
            new_download = db_user.get('download_bytes', 0) + user_traffic.download_bytes

            update_data = {
                'upload_bytes': new_upload,
                'download_bytes': new_download,
                'status': user_traffic.status,
                'online_count': user_traffic.online_count,
            }
            
            if not db_user.get('account_creation_date') and user_traffic.account_creation_date:
                update_data['account_creation_date'] = user_traffic.account_creation_date

            db.update_user(user_traffic.username, update_data)
            updated_count += 1
            
        except Exception as e:
            print(f"Error updating traffic for user {user_traffic.username}: {e}")

    return DetailResponse(detail=f"Successfully processed and aggregated traffic for {updated_count} users.")

@router.post('/nodes/heartbeat', summary='Receive Node Heartbeat')
async def receive_node_heartbeat(request: Request, body: NodeHeartbeatBody):
    NODE_STATUS_STORE[body.node_name] = {
        "stats": body.dict(),
        "last_seen": time.time(),
        "ip": request.client.host
    }
    
    command = None
    if body.node_name in NODE_COMMAND_QUEUE:
        command = NODE_COMMAND_QUEUE.pop(body.node_name)
        
    return {"status": "ok", "command": command}

@router.get('/nodes/status', summary='Get All Nodes Status')
async def get_nodes_status():
    current_time = time.time()
    results = {}
    
    configured_nodes = []
    if os.path.exists(cli_api.NODES_JSON_PATH):
        try:
            with open(cli_api.NODES_JSON_PATH, 'r') as f:
                content = f.read()
                if content:
                    configured_nodes = json.loads(content)
        except Exception: 
            pass

    for name, data in NODE_STATUS_STORE.items():
        is_online = (current_time - data['last_seen']) < 70
        results[name] = {
            **data['stats'],
            "is_online": is_online,
            "last_seen_ago": int(current_time - data['last_seen']),
            "source_ip": data.get("ip")
        }

    for node in configured_nodes:
        name = node.get('name')
        
        if name not in results:
             node_ip_raw = node.get('ip')
             found_match = False
             
             if node_ip_raw:
                 resolved_ips = {node_ip_raw}
                 try:
                     if any(c.isalpha() for c in node_ip_raw):
                         infos = socket.getaddrinfo(node_ip_raw, None)
                         for info in infos:
                             resolved_ips.add(info[4][0])
                 except: 
                     pass

                 for stored_name, stored_data in results.items():
                     stored_ip = stored_data.get('source_ip')
                     if stored_ip and stored_ip in resolved_ips:
                         results[name] = stored_data.copy()
                         results[name]['node_name'] = name 
                         found_match = True
                         break
             
             if found_match and results[name].get('is_online'):
                 continue

        if name not in results or not results[name]['is_online']:
            
            ip = node.get('ip')
            port = node.get('port')
            
            is_active = False
            if ip and port:
                try:
                    loop = asyncio.get_running_loop()
                    is_active = await loop.run_in_executor(None, check_tcp_port, ip, port)
                except Exception:
                    pass
            
            if name not in results:
                results[name] = {
                    "node_name": name,
                    "is_online": is_active,
                    "cpu_percent": 0,
                    "ram_percent": 0,
                    "uptime": "Active Check" if is_active else "Offline",
                    "hysteria_active": is_active 
                }
            elif is_active:
                results[name]['is_online'] = True
                curr_uptime = results[name].get('uptime', '-')
                if curr_uptime == '-' or curr_uptime == 'Offline':
                     results[name]['uptime'] = "Active Check"

    return results

@router.post('/nodes/restart', response_model=DetailResponse, summary='Queue Restart Command')
async def restart_node(body: RestartNodeBody):
    NODE_COMMAND_QUEUE[body.node_name] = "restart"
    return DetailResponse(detail=f"Restart command queued for node '{body.node_name}'.")

@router.post('/nodes/autoinstall', summary='Auto-install any-node via SSH')
async def autoinstall_node(body: AutoInstallNodeBody, request: Request):
    _root = CONFIGS.ROOT_PATH.strip('/') if CONFIGS.ROOT_PATH else ''
    _domain = CONFIGS.DOMAIN.strip('/')
    _scheme = 'https' if not CONFIGS.SELF_SIGNED else 'https'
    panel_url = f"{_scheme}://{_domain}" + (f'/{_root}' if _root else '')
    panel_token = CONFIGS.API_TOKEN

    async def generate():
        try:
            import paramiko
        except ImportError:
            yield "data: [✗] paramiko is not installed on the server. Run: pip install paramiko\n\n"
            yield "data: __DONE_ERR__\n\n"
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            yield f"data: [*] Connecting to {body.ssh_host}:{body.ssh_port}...\n\n"

            def _connect():
                transport = paramiko.Transport((body.ssh_host, body.ssh_port))
                transport.connect()
                transport.auth_password(body.ssh_user, body.ssh_password)
                client._transport = transport

            await asyncio.get_event_loop().run_in_executor(None, _connect)
            yield "data: [✓] Connected!\n\n"

            cmd = (
                "curl -fsSL https://raw.githubusercontent.com/0xd5f/any-node/main/install.sh"
                f" -o /tmp/_any_install.sh && chmod +x /tmp/_any_install.sh"
                f" && bash /tmp/_any_install.sh install {body.hysteria_port} {body.sni} 2>&1"
            )

            channel = client.get_transport().open_session()
            channel.get_pty(width=200, height=50)
            channel.exec_command(cmd)

            await asyncio.sleep(2)
            channel.sendall(f"{panel_url}\n".encode('utf-8'))
            await asyncio.sleep(0.5)
            channel.sendall(f"{panel_token}\n".encode('utf-8'))

            buf = b""
            while True:
                ready = await asyncio.get_event_loop().run_in_executor(None, channel.recv_ready)
                if ready:
                    chunk = await asyncio.get_event_loop().run_in_executor(None, channel.recv, 4096)
                    if not chunk:
                        break
                    buf += chunk
                    try:
                        decoded = buf.decode('utf-8', errors='replace')
                        buf = b""
                    except Exception:
                        continue
                    lines = decoded.replace('\r\n', '\n').replace('\r', '\n').split('\n')
                    for line in lines:
                        clean = line.strip()
                        if clean:
                            yield f"data: {clean}\n\n"
                    await asyncio.sleep(0)
                elif await asyncio.get_event_loop().run_in_executor(None, channel.exit_status_ready):
                    break
                else:
                    await asyncio.sleep(0.2)

            exit_code = await asyncio.get_event_loop().run_in_executor(None, channel.recv_exit_status)
            yield "data: \n\n"
            if exit_code == 0:
                yield "data: [✓] Installation completed successfully!\n\n"
                yield "data: __DONE_OK__\n\n"
            else:
                yield f"data: [✗] Installation failed (exit code {exit_code})\n\n"
                yield "data: __DONE_ERR__\n\n"

        except Exception as e:
            yield f"data: [✗] Error: {str(e)}\n\n"
            yield "data: __DONE_ERR__\n\n"
        finally:
            client.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post('/nodes/tunnel-exec', summary='Execute tunnel setup script on node via SSH')
async def tunnel_exec(body: TunnelExecBody):
    async def generate():
        try:
            import paramiko
        except ImportError:
            yield "data: [✗] paramiko not installed\n\n"
            yield "data: __DONE_ERR__\n\n"
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            yield f"data: [*] Connecting to {body.ssh_host}:{body.ssh_port}...\n\n"

            def _connect():
                transport = paramiko.Transport((body.ssh_host, body.ssh_port))
                transport.connect()
                transport.auth_password(body.ssh_user, body.ssh_password)
                client._transport = transport

            await asyncio.get_event_loop().run_in_executor(None, _connect)
            yield "data: [✓] Connected!\n\n"
            yield "data: [*] Executing tunnel setup...\n\n"

            def _upload_and_run():
                sftp = client.open_sftp()
                with sftp.open('/tmp/_tunnel_setup.sh', 'w') as f:
                    f.write(body.script)
                sftp.close()

            await asyncio.get_event_loop().run_in_executor(None, _upload_and_run)

            channel = client.get_transport().open_session()
            channel.get_pty(width=200, height=50)
            channel.exec_command('bash /tmp/_tunnel_setup.sh 2>&1')

            buf = b""
            while True:
                ready = await asyncio.get_event_loop().run_in_executor(None, channel.recv_ready)
                if ready:
                    chunk = await asyncio.get_event_loop().run_in_executor(None, channel.recv, 4096)
                    if not chunk:
                        break
                    buf += chunk
                    decoded = buf.decode('utf-8', errors='replace')
                    buf = b""
                    for line in decoded.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                        clean = line.strip()
                        if clean:
                            yield f"data: {clean}\n\n"
                    await asyncio.sleep(0)
                elif await asyncio.get_event_loop().run_in_executor(None, channel.exit_status_ready):
                    break
                else:
                    await asyncio.sleep(0.2)

            exit_code = await asyncio.get_event_loop().run_in_executor(None, channel.recv_exit_status)
            if exit_code == 0:
                yield "data: [✓] Tunnel setup completed!\n\n"
                yield "data: __DONE_OK__\n\n"
            else:
                yield f"data: [✗] Failed (exit code {exit_code})\n\n"
                yield "data: __DONE_ERR__\n\n"
        except Exception as e:
            yield f"data: [✗] Error: {str(e)}\n\n"
            yield "data: __DONE_ERR__\n\n"
        finally:
            client.close()

    return StreamingResponse(generate(), media_type="text/event-stream")