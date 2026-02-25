import os
import sys
import subprocess
import logging
import shutil
from pathlib import Path
import stat
import string
import random

PROXY_DIR = Path("/etc/3proxy")
PROXY_CONF = PROXY_DIR / "3proxy.cfg"
PROXY_USERS_FILE = PROXY_DIR / ".proxyauth"
PROXY_SETTINGS_FILE = PROXY_DIR / "proxy_settings.json"

def get_settings():
    if PROXY_SETTINGS_FILE.exists():
        try:
            import json
            with open(PROXY_SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading proxy settings: {e}")
            
    return {"socks_port": 1080, "http_port": 3128, "max_conns": 5000}

def save_settings(socks_port, http_port, max_conns):
    import json
    settings = {
        "socks_port": int(socks_port),
        "http_port": int(http_port),
        "max_conns": int(max_conns)
    }
    with open(PROXY_SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
    generate_base_config()
    systemctl("restart", "3proxy")
    return settings

def run(cmd, capture=False, check=False, shell=True):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=capture, text=True)
        stderr_text = r.stderr.strip() if r.stderr else ""
        if check and r.returncode != 0:
            logging.error(f"Command '{cmd}' failed. stderr: {stderr_text}")
            raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)
        if capture and r.returncode != 0:
            logging.error(f"Command '{cmd}' failed with code {r.returncode}. stderr: {stderr_text}")
        return r.stdout.strip() if capture else r.returncode == 0
    except Exception as e:
        if check:
            raise
        logging.error(f"Exception running '{cmd}': {e}")
        return "" if capture else False

def systemctl(action, service):
    return run(f"systemctl {action} {service}", check=True)

def cmd_exists(cmd):
    return run(f"command -v {cmd}", capture=True) != ""

def is_installed():
    return cmd_exists("3proxy") and PROXY_CONF.exists()

def generate_base_config():
    settings = get_settings()
    socks_port = settings.get("socks_port", 1080)
    http_port = settings.get("http_port", 3128)
    max_conns = settings.get("max_conns", 5000)

    # Read existing users if they exist
    users_block = ""
    if PROXY_USERS_FILE.exists():
        content = PROXY_USERS_FILE.read_text()
        for line in content.splitlines():
            if line.strip():
                users_block += f"users {line}\n"

    config = f"""nserver 8.8.8.8
nserver 8.8.4.4
nscache 65536
maxconn {max_conns}
timeouts 1 5 30 60 180 1800 15 60
log /var/log/3proxy.log D
logformat "- +_L%t.%. %N.%p %E %U %C:%c %R:%r %O %I %h %T"
auth cache strong
{users_block}
allow *
socks -p{socks_port}
proxy -p{http_port}
"""
    PROXY_CONF.write_text(config)
    PROXY_CONF.chmod(0o600)
    
    if not PROXY_USERS_FILE.exists():
        PROXY_USERS_FILE.write_text("")
        PROXY_USERS_FILE.chmod(0o600)

def install_3proxy():
    logging.info("Installing Proxy...")
    if not is_installed():
        if run("command -v apt-get", capture=True):
            # Try apt-get first
            install_res = run("apt-get update && apt-get install -y 3proxy")
            if not install_res or not cmd_exists("3proxy"):
                # Fallback to source compilation if apt fails or package doesn't exist
                logging.info("Apt install failed or not found, compiling 3proxy from source...")
                run("apt-get update && apt-get install -y build-essential gcc make git")
                run("cd /tmp && git clone https://github.com/3proxy/3proxy.git && cd 3proxy && make -f Makefile.Linux && make -f Makefile.Linux install")
                run("rm -rf /tmp/3proxy")
                if not cmd_exists("3proxy"):
                     raise Exception("Failed to install 3proxy via apt and source compilation.")
        else:
            raise Exception("Unsupported OS. Please install 3proxy manually.")
            
    PROXY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate config safely AFTER install logic to prevent make install overwriting it
    generate_base_config()

    systemctl("enable", "3proxy")
    systemctl("restart", "3proxy")
    
    settings = get_settings()
    socks_port = settings.get("socks_port", 1080)
    http_port = settings.get("http_port", 3128)

    # Open firewall ports
    run(f"iptables -C INPUT -p tcp --dport {socks_port} -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport {socks_port} -j ACCEPT")
    run(f"iptables -C INPUT -p tcp --dport {http_port} -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport {http_port} -j ACCEPT")

def uninstall_3proxy():
    logging.info("Uninstalling Proxy...")
    if run("systemctl is-active 3proxy", capture=True) == "active":
        systemctl("stop", "3proxy")
    if run("systemctl is-enabled 3proxy 2>/dev/null", capture=True) == "enabled":
        systemctl("disable", "3proxy")
        
    if cmd_exists("apt-get"):
        run("apt-get remove --purge -y 3proxy")
        run("apt-get autoremove -y")
        
    if PROXY_DIR.exists():
        shutil.rmtree(PROXY_DIR, ignore_errors=True)
        run(f"rm -rf {PROXY_DIR}", shell=True)

def add_user(username: str, password: str = None):
    if not is_installed():
        raise Exception("Proxy is not installed.")
        
    if not password:
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
    # Check if user exists
    if PROXY_USERS_FILE.exists():
        content = PROXY_USERS_FILE.read_text()
        for line in content.splitlines():
            if line.startswith(f"{username}:"):
                raise Exception(f"User {username} already exists.")
                
    # 3proxy uses plaintext format for users
    # Format: username:CL:password
    with open(PROXY_USERS_FILE, "a") as f:
        f.write(f"{username}:CL:{password}\n")
        
    generate_base_config()
    systemctl("restart", "3proxy")
    settings = get_settings()
    socks_port = settings.get("socks_port", 1080)
    http_port = settings.get("http_port", 3128)
    return {"username": username, "password": password, "socks_port": socks_port, "http_port": http_port}

def remove_user(username: str):
    if not is_installed():
        raise Exception("3Proxy is not installed.")
        
    if not PROXY_USERS_FILE.exists():
        return
        
    content = PROXY_USERS_FILE.read_text()
    new_content = []
    
    for line in content.splitlines():
        if line.startswith(f"{username}:"):
            continue
        new_content.append(line)
        
    PROXY_USERS_FILE.write_text("\n".join(new_content) + "\n" if new_content else "")
    generate_base_config()
    systemctl("restart", "3proxy")

def list_users():
    users = []
    if not is_installed() or not PROXY_USERS_FILE.exists():
        return users
        
    settings = get_settings()
    socks_port = settings.get("socks_port", 1080)
    http_port = settings.get("http_port", 3128)

    content = PROXY_USERS_FILE.read_text()
    for line in content.splitlines():
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 3:
            users.append({
                "username": parts[0],
                "password": parts[2],
                "socks_port": socks_port,
                "http_port": http_port
            })
            
    return users

def status():
    is_active = run("systemctl is-active 3proxy", capture=True) == "active"
    return {"installed": is_installed(), "active": is_active}

if __name__ == "__main__":
    import json
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "install":
        install_3proxy()
    elif cmd == "uninstall":
        uninstall_3proxy()
    elif cmd == "add":
        pwd = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(add_user(sys.argv[2], pwd)))
    elif cmd == "remove":
        remove_user(sys.argv[2])
    elif cmd == "list":
        print(json.dumps(list_users()))
    elif cmd == "status":
        print(json.dumps(status()))
    elif cmd == "get_config":
        print(json.dumps(get_settings()))
    elif cmd == "save_config":
        s_port = sys.argv[2]
        h_port = sys.argv[3]
        m_conns = sys.argv[4]
        print(json.dumps(save_settings(s_port, h_port, m_conns)))
