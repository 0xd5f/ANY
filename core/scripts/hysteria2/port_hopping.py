import init_paths
import sys
import subprocess
import argparse
import re
import json
from paths import CONFIG_FILE, CONFIG_ENV


def load_env():
    env_vars = {}
    try:
        with open(CONFIG_ENV, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip()
    except FileNotFoundError:
        pass
    return env_vars


def save_env(env_vars):
    lines = []
    try:
        with open(CONFIG_ENV, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass

    existing_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0]
            if key in env_vars:
                new_lines.append(f"{key}={env_vars[key]}\n")
                existing_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for key, value in env_vars.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}\n")

    with open(CONFIG_ENV, 'w') as f:
        f.writelines(new_lines)


def get_server_port():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config.get("listen", "").split(":")[-1]
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_default_interface():
    try:
        result = subprocess.run(
            ['ip', 'route', 'show', 'default'],
            capture_output=True, text=True, check=True
        )
        for part in result.stdout.split():
            if part == 'dev':
                idx = result.stdout.split().index('dev')
                return result.stdout.split()[idx + 1]
    except Exception:
        pass
    return 'eth0'


def parse_port_range(port_range_str):
    match = re.match(r'^(\d+)-(\d+)$', port_range_str.strip())
    if not match:
        return None, None
    start = int(match.group(1))
    end = int(match.group(2))
    if start < 1 or end > 65535 or start >= end:
        return None, None
    return start, end


def get_existing_rules(server_port):
    rules = {'v4': [], 'v6': []}
    for cmd, key in [(['iptables', '-t', 'nat', '-S', 'PREROUTING'], 'v4'),
                     (['ip6tables', '-t', 'nat', '-S', 'PREROUTING'], 'v6')]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for line in result.stdout.strip().split('\n'):
                if f'--to-ports {server_port}' in line and 'REDIRECT' in line:
                    rules[key].append(line.strip())
        except Exception:
            pass
    return rules


def remove_existing_rules(server_port):
    iface = get_default_interface()
    rules = get_existing_rules(server_port)

    for line in rules['v4']:
        try:
            delete_cmd = line.replace('-A ', '', 1)
            parts = delete_cmd.split()
            subprocess.run(['iptables', '-t', 'nat', '-D'] + parts, check=True,
                           capture_output=True)
        except Exception:
            pass

    for line in rules['v6']:
        try:
            delete_cmd = line.replace('-A ', '', 1)
            parts = delete_cmd.split()
            subprocess.run(['ip6tables', '-t', 'nat', '-D'] + parts, check=True,
                           capture_output=True)
        except Exception:
            pass


def add_iptables_rules(server_port, start_port, end_port):
    iface = get_default_interface()
    commands = [
        ['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface,
         '-p', 'udp', '--dport', f'{start_port}:{end_port}',
         '-j', 'REDIRECT', '--to-ports', str(server_port)],
        ['ip6tables', '-t', 'nat', '-A', 'PREROUTING', '-i', iface,
         '-p', 'udp', '--dport', f'{start_port}:{end_port}',
         '-j', 'REDIRECT', '--to-ports', str(server_port)],
    ]

    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: {' '.join(cmd[:2])} rule failed: {e.stderr.strip()}", file=sys.stderr)


def enable(port_range_str, hop_interval=30):
    server_port = get_server_port()
    if not server_port:
        print("Error: Could not read server port from config.", file=sys.stderr)
        sys.exit(1)

    start_port, end_port = parse_port_range(port_range_str)
    if start_port is None:
        print(f"Error: Invalid port range '{port_range_str}'. Use format: START-END (e.g., 20000-50000).",
              file=sys.stderr)
        sys.exit(1)

    if start_port <= int(server_port) <= end_port:
        pass

    remove_existing_rules(server_port)
    add_iptables_rules(server_port, start_port, end_port)

    env = load_env()
    env['PORT_HOPPING'] = 'true'
    env['PORT_HOPPING_RANGE'] = port_range_str.strip()
    env['HOP_INTERVAL'] = str(int(hop_interval))
    save_env(env)

    print(f"Port hopping enabled: {start_port}-{end_port} → {server_port} (interval: {hop_interval}s)")


def disable():
    server_port = get_server_port()
    if not server_port:
        print("Error: Could not read server port from config.", file=sys.stderr)
        sys.exit(1)

    remove_existing_rules(server_port)

    env = load_env()
    env['PORT_HOPPING'] = 'false'
    if 'PORT_HOPPING_RANGE' in env:
        del env['PORT_HOPPING_RANGE']
    if 'HOP_INTERVAL' in env:
        del env['HOP_INTERVAL']
    save_env(env)

    print("Port hopping disabled.")


def status():
    env = load_env()
    enabled = env.get('PORT_HOPPING', 'false').lower() == 'true'
    port_range = env.get('PORT_HOPPING_RANGE', '')
    hop_interval = int(env.get('HOP_INTERVAL', '30'))
    server_port = get_server_port()

    if not enabled or not port_range:
        print(json.dumps({"enabled": False, "port_range": "", "server_port": server_port or "", "iptables_active": False, "hop_interval": 30}))
        return

    try:
        rules = get_existing_rules(server_port) if server_port else {'v4': [], 'v6': []}
        has_rules = bool(rules['v4'] or rules['v6'])
    except Exception:
        has_rules = False

    print(json.dumps({
        "enabled": enabled,
        "port_range": port_range,
        "server_port": server_port or "",
        "iptables_active": has_rules,
        "hop_interval": hop_interval
    }))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    enable_parser = subparsers.add_parser('enable')
    enable_parser.add_argument('--range', type=str, required=True,
                               help='Port range (e.g., 20000-50000)')
    enable_parser.add_argument('--interval', type=int, default=30,
                               help='Hop interval in seconds (default: 30)')

    subparsers.add_parser('disable')
    subparsers.add_parser('status')

    args = parser.parse_args()

    if args.command == 'enable':
        enable(args.range, args.interval)
    elif args.command == 'disable':
        disable()
    elif args.command == 'status':
        status()


if __name__ == "__main__":
    main()
