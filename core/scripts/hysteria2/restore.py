import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path

DB_NAME = "blitz_panel"
HYSTERIA_CONFIG_DIR = Path("/etc/hysteria")
CLI_PATH = Path("/etc/hysteria/core/cli.py")

def run_command(command, check=False):
    try:
        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: '{e.cmd}'", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        raise

def main():
    if len(sys.argv) < 2:
        print("Error: Backup file path is required.", file=sys.stderr)
        return 1

    backup_zip_file = Path(sys.argv[1])

    if not backup_zip_file.is_file():
        print(f"Error: Backup file not found: {backup_zip_file}", file=sys.stderr)
        return 1

    if backup_zip_file.suffix.lower() != '.zip':
        print("Error: Backup file must be a .zip file.", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            print(f"Extracting backup to temporary directory: {temp_dir}")

            try:
                with zipfile.ZipFile(backup_zip_file) as zf:
                    zf.extractall(temp_dir)
            except zipfile.BadZipFile:
                print("Error: Invalid or corrupt ZIP file.", file=sys.stderr)
                return 1

            dump_dir = temp_dir / DB_NAME
            if not dump_dir.is_dir():
                print("Error: Backup is in an old format or is missing the database dump.", file=sys.stderr)
                print("Please use a backup created with the new MongoDB-aware script.", file=sys.stderr)
                return 1
            
            print("Restoring MongoDB database... (This will drop the current user data)")
            run_command(f"mongorestore --db={DB_NAME} --drop --dir='{dump_dir}'", check=True)
            print("Database restored successfully.")

            files_to_copy = ["config.json", ".configs.env", "ca.key", "ca.crt"]
            print("Restoring configuration files...")
            for filename in files_to_copy:
                src = temp_dir / filename
                if src.exists():
                    shutil.copy2(src, HYSTERIA_CONFIG_DIR / filename)
                    print(f" - Restored {filename}")

            adjust_config_file()

            print("Setting permissions...")
            run_command(f"chown hysteria:hysteria {HYSTERIA_CONFIG_DIR / 'ca.key'} {HYSTERIA_CONFIG_DIR / 'ca.crt'}")
            run_command(f"chmod 640 {HYSTERIA_CONFIG_DIR / 'ca.key'} {HYSTERIA_CONFIG_DIR / 'ca.crt'}")

            print("Restarting Hysteria service...")
            run_command(f"python3 {CLI_PATH} restart-hysteria2", check=True)

            print("\nRestore completed successfully.")
            return 0

    except subprocess.CalledProcessError:
        print("\nRestore failed due to a command execution error.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nAn unexpected error occurred during restore: {e}", file=sys.stderr)
        return 1

def adjust_config_file():
    config_file = HYSTERIA_CONFIG_DIR / "config.json"
    if not config_file.exists():
        return

    print("Adjusting config.json based on current system state...")
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        result = run_command("ip route | grep '^default' | awk '{print $5}'")
        network_device = result.stdout.strip()
        if network_device:
            for outbound in config.get('outbounds', []):
                if outbound.get('name') == 'v4' and 'direct' in outbound:
                    outbound['direct']['bindDevice'] = network_device
        
        result = run_command("systemctl is-active --quiet wg-quick@wgcf.service")
        if result.returncode != 0:
            print(" - WARP service is inactive, removing related configuration.")
            config['outbounds'] = [o for o in config.get('outbounds', []) if o.get('name') != 'warps']
            if 'acl' in config and 'inline' in config['acl']:
                config['acl']['inline'] = [r for r in config['acl']['inline'] if not r.startswith('warps(')]
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    except Exception as e:
        print(f"Warning: Could not adjust config.json. {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())