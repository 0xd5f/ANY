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
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        masq = config.get("masquerade")
        if not masq:
            print(json.dumps({"enabled": False, "type": "none", "url": ""}))
            return
        mtype = masq.get("type", "string")
        url = ""
        if mtype == "proxy":
            url = masq.get("proxy", {}).get("url", "")
        print(json.dumps({"enabled": True, "type": mtype, "url": url}))
    except Exception:
        print(json.dumps({"enabled": False, "type": "none", "url": ""}))

def enable_masquerade(mode="string", proxy_url=""):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        if "obfs" in config:
            print("Error: Cannot enable masquerade when 'obfs' is configured.")
            sys.exit(1)

        if mode == "proxy":
            if not proxy_url:
                print("Error: proxy URL is required for proxy mode.")
                sys.exit(1)
            config["masquerade"] = {
                "type": "proxy",
                "proxy": {
                    "url": proxy_url,
                    "rewriteHost": True
                }
            }
            print(f"Masquerade enabled in proxy mode: {proxy_url}")
        else:
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
            print("Masquerade enabled with a Caddy-like 502 Bad Gateway response.")

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

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
        print("Usage: python3 masquerade.py {1|2|status} [--mode string|proxy] [--url URL]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "1":
        mode = "string"
        proxy_url = ""
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--mode" and i + 1 < len(sys.argv):
                mode = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--url" and i + 1 < len(sys.argv):
                proxy_url = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        enable_masquerade(mode, proxy_url)
    elif action == "2":
        remove_masquerade()
    elif action == "status":
        get_status()
    else:
        print("Invalid option. Use 1, 2, or status.")
        sys.exit(1)

if __name__ == "__main__":
    main()