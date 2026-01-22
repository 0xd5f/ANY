import os
import sys
import subprocess
import platform
import logging
from pathlib import Path

WGCF_PROFILE = "wgcf-profile.conf"
WGCF_PROFILE_DIR = Path("/etc/warp")
WGCF_PROFILE_PATH = WGCF_PROFILE_DIR / WGCF_PROFILE
WG_INTERFACE = "wgcf"
WG_CONF_PATH = Path(f"/etc/wireguard/{WG_INTERFACE}.conf")
WG_DNS = "8.8.8.8,8.8.4.4,2001:4860:4860::8888,2001:4860:4860::8844"
WG_RULE_TABLE = "51888"
WG_RULE_FWMARK = "51888"
WG_PEER_ENDPOINT_IP4 = "162.159.192.1"
WG_PEER_ENDPOINT_IP6 = "2606:4700:d0::a29f:c001"
WG_PEER_ENDPOINT_DOMAIN = "engage.cloudflareclient.com:2408"
WG_ALLOWED_IPS = "0.0.0.0/0,::/0"
TEST_IPV4 = ["1.0.0.1", "9.9.9.9"]
TEST_IPV6 = ["2606:4700:4700::1001", "2620:fe::fe"]
CF_TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"


def run(cmd, capture=False, check=False, shell=True):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=capture, text=True)
        return r.stdout.strip() if capture else r.returncode == 0
    except:
        return "" if capture else False


def cmd_exists(cmd):
    return run(f"command -v {cmd}", capture=True) != ""


def systemctl(action, service):
    return run(f"systemctl {action} {service}")


def get_system_info():
    info = {"os": "", "os_full": "", "arch": platform.machine(), "virt": "", "kernel": platform.release()}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    info["os"] = line.split("=")[1].strip().strip('"').lower()
                elif line.startswith("PRETTY_NAME="):
                    info["os_full"] = line.split("=", 1)[1].strip().strip('"')
    except:
        pass
    info["virt"] = run("systemd-detect-virt", capture=True) or "none"
    kv = info["kernel"].split(".")
    info["kernel_major"] = int(kv[0]) if kv else 0
    info["kernel_minor"] = int(kv[1]) if len(kv) > 1 else 0
    return info


def ping4(host):
    return run(f"ping -c1 -W1 {host} >/dev/null 2>&1")


def ping6(host):
    return run(f"ping6 -c1 -W1 {host} >/dev/null 2>&1")


def check_ipv4():
    return any(ping4(ip) for ip in TEST_IPV4)


def check_ipv6():
    return any(ping6(ip) for ip in TEST_IPV6)


def check_warp_client():
    return run("systemctl is-active warp-svc", capture=True) == "active"


def check_wireguard():
    status = run(f"systemctl is-active wg-quick@{WG_INTERFACE}", capture=True)
    enabled = run(f"systemctl is-enabled wg-quick@{WG_INTERFACE} 2>/dev/null", capture=True)
    return status == "active", enabled == "enabled"


def install_wireguard_tools(info):
    logging.info("Installing wireguard-tools...")
    os_name = info["os"]
    if "debian" in os_name or "ubuntu" in os_name:
        run("apt update && apt install -y iproute2 resolvconf wireguard-tools --no-install-recommends")
    else:
        logging.error("OS not supported. Only Debian and Ubuntu are supported.")
        sys.exit(1)


def install_wireguard_go(info):
    need_go = info["virt"] in ["openvz", "lxc"] or info["kernel_major"] < 5 or (info["kernel_major"] == 5 and info["kernel_minor"] < 6)
    if need_go:
        run("curl -fsSL git.io/wireguard-go.sh | bash")


def install_wireguard(info):
    print(f"\nSystem: {info['os_full']} | Kernel: {info['kernel']} | Arch: {info['arch']} | Virt: {info['virt']}\n")
    active, enabled = check_wireguard()
    if not (active and enabled):
        install_wireguard_tools(info)
        install_wireguard_go(info)
    else:
        logging.info("WireGuard already installed and running.")


def install_wgcf():
    run("curl -fsSL https://raw.githubusercontent.com/0xd5f/warp/refs/heads/main/wgcf.sh | bash")


def register_warp_account():
    while not Path("wgcf-account.toml").exists():
        install_wgcf()
        logging.info("Registering WARP account...")
        run("yes | wgcf register")
        run("sleep 5")


def generate_wgcf_profile():
    while not Path(WGCF_PROFILE).exists():
        register_warp_account()
        logging.info("Generating WGCF profile...")
        run("wgcf generate")


def backup_wgcf_profile():
    WGCF_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    run(f"mv -f wgcf* {WGCF_PROFILE_DIR}")


def read_wgcf_profile():
    data = {"private_key": "", "address": "", "public_key": "", "addr_v4": "", "addr_v6": ""}
    try:
        content = WGCF_PROFILE_PATH.read_text()
        for line in content.splitlines():
            if line.startswith("PrivateKey"):
                data["private_key"] = line.split("=", 1)[1].strip()
            elif line.startswith("Address"):
                data["address"] = line.split("=", 1)[1].strip()
            elif line.startswith("PublicKey"):
                data["public_key"] = line.split("=", 1)[1].strip()
        if "," in data["address"]:
            parts = data["address"].split(",")
            data["addr_v4"] = parts[0].split("/")[0].strip()
            data["addr_v6"] = parts[1].split("/")[0].strip()
        else:
            addr = data["address"].strip()
            if ":" in addr:
                data["addr_v6"] = addr.split("/")[0]
            else:
                data["addr_v4"] = addr.split("/")[0]
    except:
        pass
    return data


def load_wgcf_profile():
    if Path(WGCF_PROFILE).exists():
        backup_wgcf_profile()
    elif not WGCF_PROFILE_PATH.exists():
        generate_wgcf_profile()
        backup_wgcf_profile()
    return read_wgcf_profile()


def get_mtu(ipv4_ok, ipv6_ok):
    logging.info("Calculating optimal MTU...")
    mtu = 1500
    increment = 10
    cmd = "ping6" if not ipv4_ok and ipv6_ok else "ping"
    test_ip = TEST_IPV6[0] if not ipv4_ok and ipv6_ok else TEST_IPV4[0]
    while True:
        if run(f"{cmd} -c1 -W1 -s{mtu - 28} -Mdo {test_ip} >/dev/null 2>&1"):
            increment = 1
            mtu += increment
        else:
            mtu -= increment
            if increment == 1:
                break
        if mtu <= 1360:
            mtu = 1360
            break
    mtu -= 80
    logging.info(f"MTU: {mtu}")
    return mtu


def get_endpoint():
    if ping4(WG_PEER_ENDPOINT_IP4):
        return f"{WG_PEER_ENDPOINT_IP4}:2408"
    if ping6(WG_PEER_ENDPOINT_IP6):
        return f"[{WG_PEER_ENDPOINT_IP6}]:2408"
    return WG_PEER_ENDPOINT_DOMAIN


def generate_config(profile, mtu, endpoint):
    config = f"""[Interface]
PrivateKey = {profile['private_key']}
Address = {profile['address']}
DNS = {WG_DNS}
MTU = {mtu}
Table = off
PostUP = ip -4 route add default dev {WG_INTERFACE} table {WG_RULE_TABLE}
PostUP = ip -4 rule add from {profile['addr_v4']} lookup {WG_RULE_TABLE}
PostDown = ip -4 rule delete from {profile['addr_v4']} lookup {WG_RULE_TABLE}
PostUP = ip -4 rule add fwmark {WG_RULE_FWMARK} lookup {WG_RULE_TABLE}
PostDown = ip -4 rule delete fwmark {WG_RULE_FWMARK} lookup {WG_RULE_TABLE}
PostUP = ip -4 rule add table main suppress_prefixlength 0
PostDown = ip -4 rule delete table main suppress_prefixlength 0
PostUP = ip -6 route add default dev {WG_INTERFACE} table {WG_RULE_TABLE}
PostUP = ip -6 rule add from {profile['addr_v6']} lookup {WG_RULE_TABLE}
PostDown = ip -6 rule delete from {profile['addr_v6']} lookup {WG_RULE_TABLE}
PostUP = ip -6 rule add fwmark {WG_RULE_FWMARK} lookup {WG_RULE_TABLE}
PostDown = ip -6 rule delete fwmark {WG_RULE_FWMARK} lookup {WG_RULE_TABLE}
PostUP = ip -6 rule add table main suppress_prefixlength 0
PostDown = ip -6 rule delete table main suppress_prefixlength 0

[Peer]
PublicKey = {profile['public_key']}
AllowedIPs = {WG_ALLOWED_IPS}
Endpoint = {endpoint}
"""
    WG_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
    WG_CONF_PATH.write_text(config)
    return config


def enable_ipv6():
    sysctl_out = run("sysctl -a 2>/dev/null | grep 'disable_ipv6.*=.*1'", capture=True)
    conf_out = run("cat /etc/sysctl.conf /etc/sysctl.d/* 2>/dev/null | grep 'disable_ipv6.*=.*1'", capture=True)
    if sysctl_out or conf_out:
        run("sed -i '/disable_ipv6/d' /etc/sysctl.conf /etc/sysctl.d/* 2>/dev/null")
        Path("/etc/sysctl.d/ipv6.conf").write_text("net.ipv6.conf.all.disable_ipv6 = 0\n")
        run("sysctl -w net.ipv6.conf.all.disable_ipv6=0")


def start_wireguard():
    warp_active = check_warp_client()
    logging.info("Starting WireGuard...")
    if warp_active:
        systemctl("stop", "warp-svc")
    systemctl("enable", f"wg-quick@{WG_INTERFACE} --now")
    if warp_active:
        systemctl("start", "warp-svc")
    active, _ = check_wireguard()
    if active:
        logging.info("WireGuard running.")
    else:
        logging.error("WireGuard failed!")
        run(f"journalctl -u wg-quick@{WG_INTERFACE} --no-pager")
        sys.exit(1)


def disable_wireguard():
    warp_active = check_warp_client()
    active, enabled = check_wireguard()
    if active or enabled:
        logging.info("Disabling WireGuard...")
        if warp_active:
            systemctl("stop", "warp-svc")
        systemctl("disable", f"wg-quick@{WG_INTERFACE} --now")
        if warp_active:
            systemctl("start", "warp-svc")
        active, enabled = check_wireguard()
        if not active and not enabled:
            logging.info("WireGuard disabled.")
        else:
            logging.error("Disable failed!")
    else:
        logging.info("WireGuard already disabled.")


def get_warp_status():
    ipv4_ok = check_ipv4()
    ipv6_ok = check_ipv6()
    v4_status = run(f"curl -s4 {CF_TRACE_URL} --connect-timeout 2 | grep warp | cut -d= -f2", capture=True) if ipv4_ok else ""
    v6_status = run(f"curl -s6 {CF_TRACE_URL} --connect-timeout 2 | grep warp | cut -d= -f2", capture=True) if ipv6_ok else ""
    def fmt(status, connected):
        if status == "on":
            return "WARP"
        if status == "plus":
            return "WARP+"
        if status == "off":
            return "Normal"
        return "Normal" if connected else "Unconnected"
    return fmt(v4_status, ipv4_ok), fmt(v6_status, ipv6_ok)


def print_status():
    logging.info("Checking status...")
    active, _ = check_wireguard()
    wg_status = "Running" if active else "Stopped"
    v4, v6 = get_warp_status()
    print(f"\n WireGuard: {wg_status}\n IPv4: {v4}\n IPv6: {v6}\n")


def install_wgx(info):
    install_wireguard(info)
    active, _ = check_wireguard()
    if active:
        systemctl("stop", f"wg-quick@{WG_INTERFACE}")
    ipv4_ok = check_ipv4()
    ipv6_ok = check_ipv6()
    profile = load_wgcf_profile()
    mtu = get_mtu(ipv4_ok, ipv6_ok)
    endpoint = get_endpoint()
    config = generate_config(profile, mtu, endpoint)
    print("\n--- Config ---")
    print(config)
    print("--- End ---\n")
    enable_ipv6()
    start_wireguard()
    print_status()


def uninstall(info):
    logging.info("Uninstalling...")
    disable_wireguard()
    WG_CONF_PATH.unlink(missing_ok=True)
    run(f"rm -rf {WGCF_PROFILE_DIR}")
    run("rm -f /usr/local/bin/wgcf")
    os_name = info["os"]
    if "debian" in os_name or "ubuntu" in os_name:
        run("apt purge -y wireguard-tools 2>/dev/null")
    logging.info("Uninstall complete.")


def print_usage():
    print("""
WARP Minimal Installer (Python)

USAGE: python3 warp.py [COMMAND]

COMMANDS:
    install     Install WARP Non-Global Network (wgx)
    uninstall   Remove WireGuard and WARP config
    status      Show current status
    help        Show this message
""")


def main():
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    if platform.system() != "Linux":
        logging.error("Linux required.")
        sys.exit(1)
    if os.geteuid() != 0:
        logging.error("Root required.")
        sys.exit(1)
    if not cmd_exists("curl"):
        logging.error("cURL required.")
        sys.exit(1)
    info = get_system_info()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd in ["install", "wgx"]:
        install_wgx(info)
    elif cmd in ["uninstall", "dwg"]:
        uninstall(info)
    elif cmd == "status":
        print_status()
    else:
        print_usage()


if __name__ == "__main__":
    main()