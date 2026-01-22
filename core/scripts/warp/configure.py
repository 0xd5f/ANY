import json
import sys
import subprocess
from pathlib import Path
import argparse
import re

core_scripts_dir = Path(__file__).resolve().parents[1]
if str(core_scripts_dir) not in sys.path:
    sys.path.append(str(core_scripts_dir))

from paths import *

def _get_current_geo_rule_stubs(inline_rules):
    geosite_stub, geoip_stub = 'geosite:ir', 'geoip:ir'
    for rule in inline_rules:
        if 'geosite:' in rule and any(country in rule for country in ['ir', 'cn', 'ru']):
            match = re.search(r'geosite:[^)]+', rule)
            if match:
                geosite_stub = match.group(0)
        if 'geoip:' in rule and any(country in rule for country in ['ir', 'cn', 'ru']):
            match = re.search(r'geoip:[^)]+', rule)
            if match:
                geoip_stub = match.group(0)
    print(f"INFO: Detected domestic geo rules: {geosite_stub}, {geoip_stub}")
    return geosite_stub, geoip_stub

def _update_acl_rules(acl_list, stubs_to_manage, target_prefix=None):
    initial_len = len(acl_list)
    
    rules_to_remove = set()
    for stub in stubs_to_manage:
        rules_to_remove.add(f"reject({stub})")
        rules_to_remove.add(f"warps({stub})")

    acl_list = [rule for rule in acl_list if rule not in rules_to_remove]
    
    rules_were_added = False
    if target_prefix:
        for stub in stubs_to_manage:
            new_rule = f"{target_prefix}({stub})"
            if new_rule not in acl_list:
                acl_list.append(new_rule)
                rules_were_added = True

    modified = (len(acl_list) != initial_len) or rules_were_added
    return acl_list, modified

def warp_configure_handler(
    set_all_traffic_state: str | None = None,
    set_popular_sites_state: str | None = None,
    set_domestic_sites_state: str | None = None,
    set_block_adult_sites_state: str | None = None
):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file {CONFIG_FILE} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {CONFIG_FILE}.")
        sys.exit(1)

    modified = False

    if 'acl' not in config: config['acl'] = {}
    if 'inline' not in config['acl']: config['acl']['inline'] = []
    
    acl_inline = config['acl']['inline']

    if set_all_traffic_state is not None:
        acl_inline, changed = _update_acl_rules(acl_inline, ['all'], 'warps' if set_all_traffic_state == 'on' else None)
        if changed:
            print(f"All traffic rule: {'Enabled' if set_all_traffic_state == 'on' else 'Disabled'}.")
            modified = True
        else:
            print(f"All traffic rule: Already {'enabled' if set_all_traffic_state == 'on' else 'disabled'}.")

    if set_popular_sites_state is not None:
        popular_stubs = ["geoip:google", "geosite:google", "geosite:netflix", "geosite:spotify"]
        target_prefix = 'warps' if set_popular_sites_state == 'on' else None
        acl_inline, changed = _update_acl_rules(acl_inline, popular_stubs, target_prefix)
        if changed:
            print(f"Popular sites rule: {'Enabled' if set_popular_sites_state == 'on' else 'Disabled'}.")
            modified = True
        else:
            print(f"Popular sites rule: Already {'enabled' if set_popular_sites_state == 'on' else 'disabled'}.")

    if set_domestic_sites_state is not None:
        geosite_stub, geoip_stub = _get_current_geo_rule_stubs(acl_inline)
        domestic_stubs = [geosite_stub, geoip_stub]
        target_prefix = 'warps' if set_domestic_sites_state == 'on' else 'reject'
        acl_inline, changed = _update_acl_rules(acl_inline, domestic_stubs, target_prefix)
        if changed:
            print(f"Domestic sites: Configured to use {'WARP' if set_domestic_sites_state == 'on' else 'REJECT'}.")
            modified = True
        else:
            print(f"Domestic sites: Already configured to use {'WARP' if set_domestic_sites_state == 'on' else 'REJECT'}.")

    if set_block_adult_sites_state is not None:
        nsfw_stub = ["geosite:nsfw"]
        target_prefix = 'reject' if set_block_adult_sites_state == 'on' else None
        acl_inline, changed = _update_acl_rules(acl_inline, nsfw_stub, target_prefix)

        if 'resolver' not in config: config['resolver'] = {}
        if 'tls' not in config['resolver']: config['resolver']['tls'] = {}
        
        desired_resolver = "1.1.1.3:853" if set_block_adult_sites_state == 'on' else "1.1.1.1:853"
        if config['resolver']['tls'].get('addr') != desired_resolver:
            config['resolver']['tls']['addr'] = desired_resolver
            print(f"Resolver: Updated to {desired_resolver}.")
            modified = True
        
        if changed:
            print(f"Adult content blocking: {'Enabled' if set_block_adult_sites_state == 'on' else 'Disabled'}.")
            modified = True
        elif not modified:
             print(f"Adult content blocking: Already {'enabled' if set_block_adult_sites_state == 'on' else 'disabled'}.")

    config['acl']['inline'] = [rule for rule in acl_inline if rule]

    if modified:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("Configuration updated. Attempting to restart hysteria2 service...")
        try:
            subprocess.run(["python3", CLI_PATH, "restart-hysteria2"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
            print("Hysteria2 service restarted successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to restart hysteria2. STDERR: {e.stderr.decode().strip()}")
        except subprocess.TimeoutExpired:
            print("Warning: Timeout expired while trying to restart hysteria2 service.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure WARP settings. At least one option must be provided.")
    parser.add_argument("--set-all", choices=['on', 'off'], help="Set WARP for all traffic (on/off)")
    parser.add_argument("--set-popular-sites", choices=['on', 'off'], help="Set WARP for popular sites (on/off)")
    parser.add_argument("--set-domestic-sites", choices=['on', 'off'], help="Set behavior for domestic sites (on=WARP, off=REJECT)")
    parser.add_argument("--set-block-adult", choices=['on', 'off'], help="Set blocking of adult content (on/off)")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(1)

    warp_configure_handler(
        set_all_traffic_state=args.set_all,
        set_popular_sites_state=args.set_popular_sites,
        set_domestic_sites_state=args.set_domestic_sites,
        set_block_adult_sites_state=args.set_block_adult
    )