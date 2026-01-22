import os
import subprocess
from enum import Enum
import sys
import requests
import json

class GeoCountry(Enum):
    IRAN = {
        'geosite': 'https://github.com/chocolate4u/Iran-v2ray-rules/releases/latest/download/geosite.dat',
        'geoip': 'https://github.com/chocolate4u/Iran-v2ray-rules/releases/latest/download/geoip.dat',
        'acl_rule_stubs': ['geosite:ir', 'geoip:ir']
    }
    CHINA = {
        'geosite': 'https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat',
        'geoip': 'https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat',
        'acl_rule_stubs': ['geosite:cn', 'geoip:cn']
    }
    RUSSIA = {
        'geosite': 'https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat',
        'geoip': 'https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat',
        'acl_rule_stubs': ['geosite:ru-available-only-inside', 'geoip:ru']
    }

GEOSITE_PATH = "/etc/hysteria/geosite.dat"
GEOIP_PATH = "/etc/hysteria/geoip.dat"
CONFIG_PATH = "/etc/hysteria/config.json"

def is_warp_active():
    try:
        subprocess.run(["systemctl", "is-active", "--quiet", "wg-quick@wgcf.service"], check=True)
        print("INFO: WARP service (wg-quick@wgcf.service) is active.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("INFO: WARP service (wg-quick@wgcf.service) is not active.")
        return False

def remove_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed existing file: {file_path}")
    except Exception as e:
        print(f"Error removing file {file_path}: {e}")

def download_file(url, destination, chunk_size=32768):
    try:
        destination_dir = os.path.dirname(destination)
        if destination_dir and not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(destination, "wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                file.write(chunk)

        print(f"File successfully downloaded to: {destination}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to download the file from '{url}'.\n{e}")
        return False
    except IOError as e:
        print(f"Error: Failed to save the file to '{destination}'.\n{e}")
        return False

def update_acl_rules(rule_stubs, warp_active):
    try:
        with open(CONFIG_PATH, 'r') as f:
            config_data = json.load(f)

        if 'acl' not in config_data or 'inline' not in config_data['acl']:
            print("ACL 'inline' section not found in config.json. Skipping update.")
            return

        all_managed_stubs = []
        for country in GeoCountry:
            all_managed_stubs.extend(country.value['acl_rule_stubs'])
        
        rules_to_remove = set()
        for stub in all_managed_stubs:
            rules_to_remove.add(f"reject({stub})")
            rules_to_remove.add(f"warps({stub})")

        current_rules = config_data['acl']['inline']
        preserved_rules = [rule for rule in current_rules if rule not in rules_to_remove]
        
        prefix = "warps" if warp_active else "reject"
        new_domestic_rules = [f"{prefix}({stub})" for stub in rule_stubs]
        print(f"Applying ACL rules with prefix '{prefix}': {new_domestic_rules}")

        config_data['acl']['inline'] = new_domestic_rules + preserved_rules
        
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"Successfully updated ACL rules in {CONFIG_PATH}")
        
    except FileNotFoundError:
        print(f"Error: Config file not found at {CONFIG_PATH}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {CONFIG_PATH}")
    except Exception as e:
        print(f"An error occurred while updating ACL rules: {e}")

def restart_hysteria_service():
    try:
        print("Restarting Hysteria service to apply changes...")
        subprocess.run(["systemctl", "restart", "hysteria-server.service"], check=True, capture_output=True, text=True)
        print("Hysteria service restarted successfully.")
    except FileNotFoundError:
        print("Error: 'systemctl' command not found. Cannot restart service.")
    except subprocess.CalledProcessError as e:
        print(f"Error restarting Hysteria service: {e}\n{e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred during service restart: {e}")


def update_geo_files(country='iran'):
    try:
        print(f"Starting geo files update for {country.upper()}...")
        country_enum = GeoCountry[country.upper()]
        
        warp_is_active = is_warp_active()
        
        remove_file(GEOSITE_PATH)
        remove_file(GEOIP_PATH)
        
        geosite_success = download_file(country_enum.value['geosite'], GEOSITE_PATH)
        geoip_success = download_file(country_enum.value['geoip'], GEOIP_PATH)

        if geosite_success and geoip_success:
            update_acl_rules(country_enum.value['acl_rule_stubs'], warp_is_active)
            restart_hysteria_service()
            print("Geo files and ACL rules update completed successfully.")
        else:
            print("Geo files update failed. ACL rules were not updated.")

    except KeyError:
        print(f"Invalid country selection. Available options: {', '.join([c.name.lower() for c in GeoCountry])}")
    except Exception as e:
        print(f"An error occurred during the update process: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in [c.name.lower() for c in GeoCountry]:
        country = sys.argv[1]
    else:
        print("Defaulting to 'iran'. Usage: python3 update_geo.py [iran|china|russia]")
        country = 'iran'
    update_geo_files(country)