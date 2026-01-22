import subprocess
import json
import shutil
import sys
from pathlib import Path

core_scripts_dir = Path(__file__).resolve().parents[1]

if str(core_scripts_dir) not in sys.path:
    sys.path.append(str(core_scripts_dir))

from paths import CONFIG_FILE, CLI_PATH 

WARP_SCRIPT_PATH = Path(__file__).resolve().parent / "warp.py"
TEMP_CONFIG = Path("/etc/hysteria/config_temp.json")


def systemctl_active(service: str) -> bool:
    return subprocess.run(["systemctl", "is-active", "--quiet", service]).returncode == 0


def load_config(path: Path):
    if not path.exists():
        print(f"❌ Config file not found: {path}")
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Could not decode JSON from config file: {path}")
        return None


def save_config(config: dict, path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    shutil.move(str(path), str(CONFIG_FILE))


def reset_acl_inline(config: dict):
    acl_inline = config.get("acl", {}).get("inline", [])
    if not acl_inline:
        return config

    new_rules = []

    rules_to_remove = {
        "warps(all)",
        "warps(geoip:google)", "warps(geosite:google)",
        "warps(geosite:netflix)", "warps(geosite:spotify)",
        "warps(geosite:openai)", "warps(geoip:openai)" 
    }
    
    for rule in acl_inline:
        if rule in rules_to_remove:
            continue

        if rule.startswith("warps("):
            new_rules.append(rule.replace("warps(", "reject(", 1))
        else:
            new_rules.append(rule)
            
    config["acl"]["inline"] = new_rules
    print("🔧 ACL rules reset from WARP-specific settings.")
    return config


def remove_warp_outbound(config: dict):
    config["outbounds"] = [
        o for o in config.get("outbounds", [])
        if not (o.get("name") == "warps")
    ]
    return config


def remove_adult_content_blocking_rule(config: dict):
    inline = config.get("acl", {}).get("inline", [])
    rule_to_remove = "reject(geosite:nsfw)"
    if rule_to_remove in inline:
        config["acl"]["inline"] = [i for i in inline if i != rule_to_remove]
        print("🔒 Adult content blocking rule removed.")
    return config


def set_dns(config: dict):
    config.setdefault("resolver", {}).setdefault("tls", {})["addr"] = "1.1.1.1:853"
    print("🔧 DNS resolver reset to 1.1.1.1.")
    return config


def restart_hysteria():
    subprocess.run(["python3", str(CLI_PATH), "restart-hysteria2"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    if systemctl_active("wg-quick@wgcf.service"):
        print("🧹 Uninstalling WARP...")
        subprocess.run([sys.executable, str(WARP_SCRIPT_PATH), "uninstall"])
        config = load_config(CONFIG_FILE)
        if config:
            config = reset_acl_inline(config)
            config = remove_warp_outbound(config)
            config = remove_adult_content_blocking_rule(config)
            config = set_dns(config)
            save_config(config, TEMP_CONFIG)
            restart_hysteria()
            print("✅ WARP uninstalled and configuration reset.")
    else:
        print("ℹ️ WARP is not active. Skipping uninstallation.")


if __name__ == "__main__":
    main()