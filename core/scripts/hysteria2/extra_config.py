import json
import argparse
import os
import sys
from init_paths import *
from paths import *
VALID_PROTOCOLS = ("vmess://", "vless://", "ss://", "trojan://")

def read_configs():
    if not os.path.exists(EXTRA_CONFIG_PATH):
        return []
    try:
        with open(EXTRA_CONFIG_PATH, 'r') as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []

def write_configs(configs):
    try:
        os.makedirs(os.path.dirname(EXTRA_CONFIG_PATH), exist_ok=True)
        with open(EXTRA_CONFIG_PATH, 'w') as f:
            json.dump(configs, f, indent=4)
    except IOError as e:
        print(f"Error writing to {EXTRA_CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

def add_config(name, uri):
    if not any(uri.startswith(protocol) for protocol in VALID_PROTOCOLS):
        print(f"Error: Invalid URI. Must start with one of {', '.join(VALID_PROTOCOLS)}", file=sys.stderr)
        sys.exit(1)

    configs = read_configs()
    
    if any(c['name'] == name for c in configs):
        print(f"Error: A configuration with the name '{name}' already exists.", file=sys.stderr)
        sys.exit(1)

    input_uri = uri.strip()
    if any(c.get('uri', '').strip() == input_uri for c in configs):
        print(f"Error: A configuration with this URI already exists.", file=sys.stderr)
        sys.exit(1)

    configs.append({
        "name": name,
        "uri": uri,
        "enabled": True
    })
    write_configs(configs)
    print(f"Successfully added configuration '{name}'.")


def edit_config(name, new_name=None, new_uri=None, enabled=None):
    configs = read_configs()
    config = next((c for c in configs if c['name'] == name), None)
    
    if not config:
        print(f"Error: No configuration found with the name '{name}'.", file=sys.stderr)
        sys.exit(1)

    if new_uri and not any(new_uri.startswith(protocol) for protocol in VALID_PROTOCOLS):
        print(f"Error: Invalid URI. Must start with one of {', '.join(VALID_PROTOCOLS)}", file=sys.stderr)
        sys.exit(1)

    if new_name and new_name != name:
         if any(c['name'] == new_name for c in configs):
            print(f"Error: A configuration with the name '{new_name}' already exists.", file=sys.stderr)
            sys.exit(1)
         config['name'] = new_name
    
    if new_uri:
        config['uri'] = new_uri
    
    if enabled is not None:
        if isinstance(enabled, str):
            config['enabled'] = enabled.lower() == 'true'
        else:
            config['enabled'] = bool(enabled)

    write_configs(configs)
    print(f"Successfully edited configuration '{name}'.")

def delete_config(name):
    configs = read_configs()
    
    initial_length = len(configs)
    configs = [c for c in configs if c['name'] != name]
    
    if len(configs) == initial_length:
        print(f"Error: No configuration found with the name '{name}'.", file=sys.stderr)
        sys.exit(1)
        
    write_configs(configs)
    print(f"Successfully deleted configuration '{name}'.")

def list_configs():
    configs = read_configs()
    print(json.dumps(configs, indent=4))

def get_config(name):
    configs = read_configs()
    config = next((c for c in configs if c['name'] == name), None)
    
    if config:
        print(json.dumps(config, indent=4))
    else:
        print(f"Error: No configuration found with the name '{name}'.", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Manage extra proxy configurations for subscription links.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_add = subparsers.add_parser("add", help="Add a new proxy configuration.")
    parser_add.add_argument("--name", type=str, required=True, help="A unique name for the configuration.")
    parser_add.add_argument("--uri", type=str, required=True, help="The proxy URI (vmess, vless, ss, trojan).")

    parser_delete = subparsers.add_parser("delete", help="Delete a proxy configuration.")
    parser_delete.add_argument("--name", type=str, required=True, help="The name of the configuration to delete.")
    
    parser_edit = subparsers.add_parser("edit", help="Edit a proxy configuration.")
    parser_edit.add_argument("--name", type=str, required=True, help="The original name of the configuration.")
    parser_edit.add_argument("--new-name", type=str, required=False, help="The new name for the configuration.")
    parser_edit.add_argument("--uri", type=str, required=False, help="The new URI.")
    parser_edit.add_argument("--enabled", type=str, required=False, choices=['true', 'false'], help="Set enabled state.")

    subparsers.add_parser("list", help="List all extra proxy configurations.")

    parser_get = subparsers.add_parser("get", help="Get a specific proxy configuration by name.")
    parser_get.add_argument("--name", type=str, required=True, help="The name of the configuration to retrieve.")
    
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("This script must be run as root.", file=sys.stderr)
        sys.exit(1)

    if args.command == "add":
        add_config(args.name, args.uri)
    elif args.command == "edit":
        edit_config(args.name, args.new_name, args.uri, args.enabled)
    elif args.command == "delete":
        delete_config(args.name)
    elif args.command == "list":
        list_configs()
    elif args.command == "get":
        get_config(args.name)

if __name__ == "__main__":
    main()