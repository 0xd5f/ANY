import json
import subprocess
import sys
from init_paths import *
from paths import *


def is_masquerade_enabled():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return "masquerade" in config
    except Exception:
        return False

def get_status():
    if is_masquerade_enabled():
        print("Enabled")
    else:
        print("Disabled")

def enable_masquerade():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        if "masquerade" in config:
            print("Masquerade is already enabled.")
            sys.exit(0)

        if "obfs" in config:
            print("Error: Cannot enable masquerade when 'obfs' is configured.")
            sys.exit(1)

        config["masquerade"] = {
            "type": "string",
            "string": {
                "content": "HTTP 502: Bad Gateway",
                "headers": {
                    "Content-Type": "text/plain; charset=utf-8",
                    "Server": "Caddy"
                },
                "statusCode": 502
            }
        }

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        print("Masquerade enabled with a Caddy-like 502 Bad Gateway response.")
        subprocess.run(["python3", CLI_PATH, "restart-hysteria2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"Failed to enable masquerade: {e}")
        sys.exit(1)

def remove_masquerade():
    if not is_masquerade_enabled():
        print("Masquerade is not enabled.")
        sys.exit(0)

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        config.pop("masquerade", None)

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        print("Masquerade removed from config.json")
        subprocess.run(["python3", CLI_PATH, "restart-hysteria2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"Failed to remove masquerade: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 masquerade.py {1|2|status}")
        print("1: Enable Masquerade")
        print("2: Remove Masquerade")
        print("status: Get current status")
        sys.exit(1)

    action = sys.argv[1]

    if action == "1":
        enable_masquerade()
    elif action == "2":
        remove_masquerade()
    elif action == "status":
        get_status()
    else:
        print("Invalid option. Use 1, 2, or status.")
        sys.exit(1)

if __name__ == "__main__":
    main()