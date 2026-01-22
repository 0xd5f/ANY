import init_paths
import os
import sys
import json
import subprocess
import argparse
import re
import qrcode
from io import StringIO
from typing import Tuple, Optional, Dict, List, Any
from db.database import db
from paths import *

def load_env_file(env_file: str) -> Dict[str, str]:
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    return env_vars

def load_nodes() -> List[Dict[str, Any]]:
    if NODES_JSON_PATH.exists():
        try:
            with NODES_JSON_PATH.open("r") as f:
                content = f.read()
                if content:
                    return json.loads(content)
        except (json.JSONDecodeError, IOError):
            pass
    return []

def load_hysteria2_env() -> Dict[str, str]:
    return load_env_file(CONFIG_ENV)

def load_hysteria2_ips() -> Tuple[str, str, str]:
    env_vars = load_hysteria2_env()
    ip4 = env_vars.get('IP4', 'None')
    ip6 = env_vars.get('IP6', 'None')
    sni = env_vars.get('SNI', '')
    return ip4, ip6, sni

def get_singbox_domain_and_port() -> Tuple[str, str]:
    env_vars = load_env_file(SINGBOX_ENV)
    domain = env_vars.get('HYSTERIA_DOMAIN', '')
    port = env_vars.get('HYSTERIA_PORT', '')
    return domain, port

def get_normalsub_domain_and_port() -> Tuple[str, str, str]:
    env_vars = load_env_file(NORMALSUB_ENV)
    domain = env_vars.get('HYSTERIA_DOMAIN', '')
    port = env_vars.get('HYSTERIA_PORT', '')
    subpath = env_vars.get('SUBPATH', '')
    return domain, port, subpath

def is_service_active(service_name: str) -> bool:
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', '--quiet', service_name],
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False

def generate_uri(username: str, auth_password: str, ip: str, port: str, 
                 obfs_password: str, sha256: str, sni: str, ip_version: int, 
                 insecure: bool, fragment_tag: str) -> str:
    ip_part = f"[{ip}]" if ip_version == 6 and ':' in ip else ip
    uri_base = f"hy2://{username}:{auth_password}@{ip_part}:{port}"
    
    params = []
    if obfs_password:
        params.append(f"obfs=salamander&obfs-password={obfs_password}")
    if sha256:
        params.append(f"pinSHA256={sha256}")
    if sni:
        params.append(f"sni={sni}")
    
    params.append(f"insecure={'1' if insecure else '0'}")
    
    query_string = "&".join(params)
    return f"{uri_base}?{query_string}#{fragment_tag}"

def generate_qr_code(uri: str) -> List[str]:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        output = StringIO()
        qr.print_ascii(out=output, invert=True)
        return output.getvalue().splitlines()
    except Exception as e:
        return [f"Error generating QR code: {str(e)}"]

def center_text(text: str, width: int) -> str:
    return text.center(width)

def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except (AttributeError, OSError):
        return 80

def display_uri_and_qr(uri: str, label: str, args: argparse.Namespace, terminal_width: int):
    if not uri:
        return
        
    print(f"\n{label}:\n{uri}\n")
    
    if args.qrcode:
        print(f"{label} QR Code:\n")
        qr_code = generate_qr_code(uri)
        for line in qr_code:
            print(center_text(line, terminal_width))

def show_uri(args: argparse.Namespace) -> None:
    if db is None:
        print("\033[0;31mError:\033[0m Database connection failed.")
        return

    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"\033[0;31mError:\033[0m Could not load config file {CONFIG_FILE}. Details: {e}")
        return

    user_doc = db.get_user(args.username)
    if not user_doc:
        print(f"\033[0;31mError:\033[0m User '{args.username}' not found in the database.")
        return
    
    auth_password = user_doc["password"]

    local_port = config["listen"].split(":")[-1]
    local_sha256 = config.get("tls", {}).get("pinSHA256", "")
    local_obfs_password = config.get("obfs", {}).get("salamander", {}).get("password", "")
    local_insecure = config.get("tls", {}).get("insecure", True)
    
    ip4, ip6, local_sni = load_hysteria2_ips()
    nodes = load_nodes()
    terminal_width = get_terminal_width()

    if args.all or args.ip_version == 4:
        if ip4 and ip4 != "None":
            uri = generate_uri(args.username, auth_password, ip4, local_port, 
                                 local_obfs_password, local_sha256, local_sni, 4, local_insecure, "IPv4")
            display_uri_and_qr(uri, "IPv4", args, terminal_width)
            
    if args.all or args.ip_version == 6:
        if ip6 and ip6 != "None":
            uri = generate_uri(args.username, auth_password, ip6, local_port, 
                                 local_obfs_password, local_sha256, local_sni, 6, local_insecure, "IPv6")
            display_uri_and_qr(uri, "IPv6", args, terminal_width)

    for node in nodes:
        node_name = node.get("name")
        node_ip = node.get("ip")
        if not node_name or not node_ip:
            continue
            
        ip_v = 4 if '.' in node_ip else 6
        
        if args.all or args.ip_version == ip_v:
            node_port = node.get("port", local_port)
            node_sni = node.get("sni", local_sni)
            node_obfs = node.get("obfs", local_obfs_password)
            node_pin = node.get("pinSHA256", local_sha256)
            node_insecure = node.get("insecure", local_insecure)

            uri = generate_uri(
                username=args.username,
                auth_password=auth_password,
                ip=node_ip,
                port=str(node_port),
                obfs_password=node_obfs,
                sha256=node_pin,
                sni=node_sni,
                ip_version=ip_v,
                insecure=node_insecure,
                fragment_tag=node_name
            )
            display_uri_and_qr(uri, f"Node: {node_name} (IPv{ip_v})", args, terminal_width)

    if args.singbox and is_service_active("hysteria-singbox.service"):
        domain, port = get_singbox_domain_and_port()
        if domain and port:
            print(f"\nSingbox Sublink:\nhttps://{domain}:{port}/sub/singbox/{args.username}/{args.ip_version}#Hysteria2\n")
    
    if args.normalsub:
        if True:
            domain, port, subpath = get_normalsub_domain_and_port()
            if domain:
                port_part = f":{port}" if port and port != "80" and port != "443" else ""
                print(f"\nNormal-SUB Sublink:\nhttps://{domain}{port_part}/{subpath}/{auth_password}#Hysteria2\n")

def main():
    parser = argparse.ArgumentParser(description="Hysteria2 URI Generator")
    parser.add_argument("-u", "--username", help="Username to generate URI for")
    parser.add_argument("-qr", "--qrcode", action="store_true", help="Generate QR code")
    parser.add_argument("-ip", "--ip-version", type=int, default=4, choices=[4, 6], 
                        help="IP version (4 or 6)")
    parser.add_argument("-a", "--all", action="store_true", help="Show all available IPs")
    parser.add_argument("-s", "--singbox", action="store_true", help="Generate SingBox sublink")
    parser.add_argument("-n", "--normalsub", action="store_true", help="Generate Normal-SUB sublink")
    
    args = parser.parse_args()
    
    if not args.username:
        parser.print_help()
        sys.exit(1)
    
    show_uri(args)

if __name__ == "__main__":
    main()