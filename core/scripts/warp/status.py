import json
from pathlib import Path
import sys
import re

core_scripts_dir = Path(__file__).resolve().parents[1]
if str(core_scripts_dir) not in sys.path:
    sys.path.append(str(core_scripts_dir))

from paths import *

def check_warp_configuration():
    status_data = {}

    if not Path(CONFIG_FILE).exists():
        status_data["error"] = f"Config file not found at {CONFIG_FILE}"
        print(json.dumps(status_data, indent=4))
        return

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        status_data["error"] = f"Invalid JSON in config file: {CONFIG_FILE}"
        print(json.dumps(status_data, indent=4))
        return

    acl_inline = config.get("acl", {}).get("inline", [])

    def contains_any_rule(rule_patterns):
        for rule in acl_inline:
            for pattern in rule_patterns:
                if re.search(pattern, rule):
                    return True
        return False

    status_data["all_traffic_via_warp"] = "warps(all)" in acl_inline
    
    popular_site_patterns = [
        r"warps\(geosite:google\)",
        r"warps\(geoip:google\)",
        r"warps\(geosite:netflix\)",
        r"warps\(geosite:spotify\)"
    ]
    status_data["popular_sites_via_warp"] = contains_any_rule(popular_site_patterns)

    domestic_site_patterns = [
        r"warps\(geosite:ir\)",
        r"warps\(geoip:ir\)",
        r"warps\(geosite:cn\)",
        r"warps\(geoip:cn\)",
        r"warps\(geosite:ru-available-only-inside\)",
        r"warps\(geoip:ru\)"
    ]
    status_data["domestic_sites_via_warp"] = contains_any_rule(domestic_site_patterns)
    
    status_data["block_adult_content"] = "reject(geosite:nsfw)" in acl_inline
    
    print(json.dumps(status_data, indent=4))

if __name__ == "__main__":
    check_warp_configuration()