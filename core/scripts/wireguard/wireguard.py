import os
import sys
import subprocess
import platform
import logging
import shutil
from pathlib import Path
import ipaddress
import urllib.request
from typing import List, Dict

WG_INTERFACE = "wg0"
WG_CONF_DIR = Path("/etc/wireguard")
WG_CONF_PATH = WG_CONF_DIR / f"{WG_INTERFACE}.conf"
WG_CLIENTS_DIR = WG_CONF_DIR / "clients"
WG_SERVER_PORT = 51820
WG_SERVER_IP = "10.77.77.1"
WG_SUBNET = "10.77.77.0/24"


def run(cmd, capture=False, check=False, shell=True, input_text=None):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=capture, text=True, input=input_text)
        if check and r.returncode != 0:
            logging.error(f"Command '{cmd}' failed. stderr: {r.stderr.strip()}")
            raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)
        if capture and r.returncode != 0:
            logging.error(f"Command '{cmd}' failed with code {r.returncode}. stderr: {r.stderr.strip()}")
        return r.stdout.strip() if capture else r.returncode == 0
    except Exception as e:
        if check:
            raise
        logging.error(f"Exception running '{cmd}': {e}")
        return "" if capture else False


def cmd_exists(cmd):
    return run(f"command -v {cmd}", capture=True) != ""


def systemctl(action, service):
    return run(f"systemctl {action} {service}", check=True)


def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as response:
            return response.read().decode('utf-8').strip()
    except:
        return ""


def check_wireguard():
    status = run(f"systemctl is-active wg-quick@{WG_INTERFACE}", capture=True)
    enabled = run(f"systemctl is-enabled wg-quick@{WG_INTERFACE} 2>/dev/null", capture=True)
    return status == "active", enabled == "enabled"


def is_installed():
    return WG_CONF_DIR.exists() and shutil.which(get_wg_bin()) is not None


def install_wireguard():
    logging.info("Installing WireGuard...")
    if not is_installed():
        if run("command -v apt-get", capture=True):
            run("apt-get update && apt-get install -y wireguard wireguard-tools qrencode iptables")
        else:
            raise Exception("Unsupported OS for automated install. Please install wireguard manually.")
    
    WG_CONF_DIR.mkdir(parents=True, exist_ok=True)
    WG_CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not WG_CONF_PATH.exists():
        generate_server_config()

    systemctl("enable", f"wg-quick@{WG_INTERFACE}")
    systemctl("start", f"wg-quick@{WG_INTERFACE}")

    # Enable IP forwarding
    run("sysctl -w net.ipv4.ip_forward=1")
    run("sed -i '/net.ipv4.ip_forward/d' /etc/sysctl.conf")
    run("echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf")
    
    # Open firewall port
    run(f"iptables -C INPUT -p udp --dport {WG_SERVER_PORT} -j ACCEPT 2>/dev/null || iptables -A INPUT -p udp --dport {WG_SERVER_PORT} -j ACCEPT")


def get_wg_bin():
    if os.name == 'nt':
        return "wg.exe"
    return shutil.which("wg") or "/usr/bin/wg"

def _run_wg_cmd(args, input_text=None):
    wg_bin = get_wg_bin()
    
    if input_text is not None:
        import tempfile
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write(input_text.strip() + "\n")
            temp_path = f.name
            
        try:
            cmd = f"{wg_bin} {' '.join(args)} < {temp_path}"
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        finally:
            os.unlink(temp_path)
    else:
        cmd = [wg_bin] + args
        r = subprocess.run(cmd, capture_output=True, text=True)
        
    if r.returncode != 0:
        if input_text:
            raise Exception(f"WireGuard error: {r.stderr.strip()} (Input length was {len(input_text)} chars)")
        else:
            raise Exception(f"WireGuard error: {r.stderr.strip()}")
            
    return r.stdout.strip()

def generate_keypair():
    privkey = _run_wg_cmd(["genkey"])
    pubkey = _run_wg_cmd(["pubkey"], input_text=privkey + "\n")
    return privkey, pubkey


def get_default_network_interface():
    try:
        route_out = run("ip route list default", capture=True)
        parts = route_out.split()
        if "dev" in parts:
            idx = parts.index("dev")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except:
        pass
        
    intf = run("ip -4 route ls | grep default | grep -Po '(?<=dev )(\\S+)'", capture=True)
    if not intf:
        intf = "eth0"
    return intf


def generate_server_config():
    privkey, pubkey = generate_keypair()
    interface = get_default_network_interface()
    
    config = f"""[Interface]
Address = {WG_SERVER_IP}/24
ListenPort = {WG_SERVER_PORT}
PrivateKey = {privkey}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {interface} -j MASQUERADE
"""
    WG_CONF_PATH.write_text(config)
    WG_CONF_PATH.chmod(0o600)
    return privkey, pubkey


def get_next_available_ip():
    subnet = ipaddress.IPv4Network(WG_SUBNET)
    used_ips = [ipaddress.IPv4Address(WG_SERVER_IP)]
    
    # Check existing client configs
    for client_file in WG_CLIENTS_DIR.glob("*.conf"):
        with open(client_file, 'r') as f:
            for line in f.readlines():
                if line.strip().startswith("Address="):
                    ip_str = line.split("=")[1].strip().split("/")[0]
                    used_ips.append(ipaddress.IPv4Address(ip_str))
                    
    for ip in subnet.hosts():
        if ip not in used_ips:
            return str(ip)
    
    raise Exception("No more available IPs in subnet")


def add_client(client_name: str):
    if not is_installed():
        raise Exception("WireGuard is not installed.")
        
    client_conf_path = WG_CLIENTS_DIR / f"{client_name}.conf"
    if client_conf_path.exists():
        raise Exception(f"Client {client_name} already exists.")

    client_privkey, client_pubkey = generate_keypair()
    
    # Get server public key
    server_conf = WG_CONF_PATH.read_text()
    server_privkey = None
    for line in server_conf.splitlines():
        if line.strip().startswith("PrivateKey"):
            server_privkey = line.split("=")[1].strip()
            break
            
    try:
        if not server_privkey or len(server_privkey) < 40:
            raise Exception("Invalid or missing PrivateKey")
        server_pubkey = _run_wg_cmd(["pubkey"], input_text=server_privkey.strip() + "\n")
    except Exception as e:
        logging.warning(f"Corrupted server config detected ({e}). Auto-healing and regenerating wg0.conf...")
        run(f"systemctl stop wg-quick@{WG_INTERFACE}", shell=True)
        server_privkey, server_pubkey = generate_server_config()
        run(f"systemctl start wg-quick@{WG_INTERFACE}", shell=True)
    
    client_ip = get_next_available_ip()
    public_ip = get_public_ip()
    
    if not public_ip:
         # Fallback to config reading IP logic if needed, but get_public_ip is usually fine.
         public_ip = "127.0.0.1" 
         
    endpoint = f"{public_ip}:{WG_SERVER_PORT}"
    
    # Generate client config
    client_config = f"""[Interface]
PrivateKey = {client_privkey}
Address = {client_ip}/24
DNS = 8.8.8.8

[Peer]
PublicKey = {server_pubkey}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    client_conf_path.write_text(client_config)
    client_conf_path.chmod(0o600)

    # Append peer to server config
    server_peer_config = f"""
### Client {client_name}
[Peer]
PublicKey = {client_pubkey}
AllowedIPs = {client_ip}/32
"""
    with open(WG_CONF_PATH, "a") as f:
        f.write(server_peer_config)
        
    # Reload wireguard by hard restarting the service exactly like the manual script
    run(f"systemctl restart wg-quick@{WG_INTERFACE}", shell=True)
    return {
        "name": client_name,
        "ip": client_ip,
        "pubkey": client_pubkey
    }


def list_clients():
    clients = []
    if not is_installed():
        return clients

    if not WG_CONF_PATH.exists():
        return clients

    content = WG_CONF_PATH.read_text()
    lines = content.splitlines()
    
    current_client = None
    for line in lines:
        if line.startswith("### Client "):
            name = line.replace("### Client ", "").strip()
            current_client = {"name": name, "enabled": True}
        elif current_client and line.startswith("AllowedIPs"):
            ip = line.split("=")[1].strip()
            current_client["ip"] = ip
            clients.append(current_client)
            current_client = None
            
    # Check ifwg show has any data for these clients (like last handshake)
    wg_show = run(f"wg show {WG_INTERFACE} dump", capture=True)
    # Output format:
    # pubkey preshared_key endpoint allowed_ips latest_handshake transfer_rx transfer_tx persistent_keepalive
    
    if wg_show:
        stats_lines = wg_show.strip().split('\n')[1:] # Skip first line (server interface stats)
        for stat in stats_lines:
            parts = stat.split('\t')
            if len(parts) >= 8:
                pubkey, _, endpoint, allowed_ips, latest_handshake, rx, tx, _ = parts
                
                # Try to map back to our dictionary
                for client in clients:
                    if client.get("ip") == allowed_ips:
                        client["rx"] = int(rx)
                        client["tx"] = int(tx)
                        client["latest_handshake"] = int(latest_handshake)
                        client["endpoint"] = endpoint if endpoint != "(none)" else None
                        
    return clients


def remove_client(client_name: str):
    if not is_installed():
        raise Exception("WireGuard is not installed.")

    client_conf_path = WG_CLIENTS_DIR / f"{client_name}.conf"
    
    # Remove from server config
    content = WG_CONF_PATH.read_text()
    new_content = []
    skip = False
    
    pubkey_to_remove = None
    
    for line in content.splitlines():
        if line.startswith(f"### Client {client_name}"):
            skip = True
            continue
            
        if skip:
            if line.startswith("PublicKey = "):
                pubkey_to_remove = line.split("=")[1].strip()
            if line.strip() == "":
                # End of block
                skip = False
            elif line.startswith("### Client ") or line.startswith("[Interface]"):
                # Hit another block, something is wrong with formatting but recover
                skip = False
                new_content.append(line)
            continue
            
        new_content.append(line)
        
    WG_CONF_PATH.write_text("\n".join(new_content) + "\n")
    
    # Remove client file
    if client_conf_path.exists():
        client_conf_path.unlink()
        
    # Remove from active interface
    if pubkey_to_remove:
        run(f"wg set {WG_INTERFACE} peer {pubkey_to_remove} remove")


def uninstall_wireguard():
    logging.info("Uninstalling WireGuard...")
    if run(f"systemctl is-active wg-quick@{WG_INTERFACE}", capture=True) == "active":
        systemctl("stop", f"wg-quick@{WG_INTERFACE}")
    if run(f"systemctl is-enabled wg-quick@{WG_INTERFACE} 2>/dev/null", capture=True) == "enabled":
        systemctl("disable", f"wg-quick@{WG_INTERFACE}")
        
    if cmd_exists("apt-get"):
        run("apt-get remove --purge -y wireguard wireguard-tools qrencode")
        run("apt-get autoremove -y")
        
    import shutil
    if WG_CONF_DIR.exists():
        shutil.rmtree(WG_CONF_DIR, ignore_errors=True)
        run(f"rm -rf {WG_CONF_DIR}", shell=True)
        
    # Disable IP forwarding (optional, but good practice if it was the only thing using it)
    run("sed -i 's/^net.ipv4.ip_forward=1/#net.ipv4.ip_forward=1/' /etc/sysctl.conf")
    run("sysctl -p")


def get_client_config(client_name: str) -> str:
    client_conf_path = WG_CLIENTS_DIR / f"{client_name}.conf"
    if client_conf_path.exists():
        return client_conf_path.read_text()
    return None

if __name__ == "__main__":
    import json
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "install":
        install_wireguard()
    elif cmd == "uninstall":
        uninstall_wireguard()
    elif cmd == "add":
        print(add_client(sys.argv[2]))
    elif cmd == "remove":
        remove_client(sys.argv[2])
    elif cmd == "list":
        print(json.dumps(list_clients()))
    elif cmd == "get_config":
        print(get_client_config(sys.argv[2]) or "")
    elif cmd == "status":
        active, enabled = check_wireguard()
        print(json.dumps({"installed": is_installed(), "active": active, "enabled": enabled}))
