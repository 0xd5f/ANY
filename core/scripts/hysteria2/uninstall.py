import os
import subprocess
import sys
from pathlib import Path

try:
    import pymongo
except ImportError:
    pymongo = None

SERVICES = [
    "hysteria-server.service",
    "hysteria-auth.service",
    "hysteria-webpanel.service",
    "hysteria-caddy.service",
    "hysteria-telegram-bot.service",
    "hysteria-normal-sub.service",
    "hysteria-singbox.service",
    "hysteria-ip-limit.service",
    "hysteria-scheduler.service",
]

DB_NAME = "blitz_panel"

def run_command(command, error_message):
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"Warning: {error_message}")
        return False
    except FileNotFoundError:
        print(f"Warning: Command not found: {command[0]}")
        return False

def drop_mongodb_database():
    if not pymongo:
        print("Warning: pymongo library not found. Skipping database cleanup.")
        return

    print(f"Attempting to drop MongoDB database: '{DB_NAME}'...")
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        client.server_info()
        client.drop_database(DB_NAME)
        print(f"Database '{DB_NAME}' dropped successfully.")
    except pymongo.errors.ConnectionFailure:
        print("Warning: Could not connect to MongoDB. Skipping database cleanup.")
    except Exception as e:
        print(f"An error occurred during database cleanup: {e}")

def uninstall_hysteria():
    print("Uninstalling Hysteria2 and all related components...")

    print("\nStep 1: Stopping and disabling all Hysteria services...")
    for service in SERVICES:
        run_command(["systemctl", "stop", service], f"Failed to stop {service}.")
        run_command(["systemctl", "disable", service], f"Failed to disable {service}.")

    print("\nStep 2: Removing systemd service files...")
    systemd_path = Path("/etc/systemd/system")
    for service in SERVICES:
        service_file = systemd_path / service
        if service_file.exists():
            run_command(["rm", "-f", str(service_file)], f"Failed to remove {service_file}")
    
    print("Reloading systemd daemon...")
    run_command(["systemctl", "daemon-reload"], "Failed to reload systemd daemon.")

    print("\nStep 3: Removing Hysteria binaries...")
    run_command(["bash", "-c", "curl -fsSL https://get.hy2.sh/ | bash -- --remove"], "Failed to run the official Hysteria uninstallation script.")

    print("\nStep 4: Cleaning MongoDB database...")
    drop_mongodb_database()

    print("\nStep 5: Removing related components (WARP)...")
    cli_path = "/etc/hysteria/core/cli.py"
    if os.path.exists(cli_path):
        run_command([sys.executable, cli_path, "uninstall-warp"], "Failed during WARP removal.")
    else:
        print("Skipping WARP removal (CLI path not found)")

    print("\nStep 6: Removing all Hysteria panel files...")
    run_command(["rm", "-rf", "/etc/hysteria"], "Failed to remove the /etc/hysteria folder.")

    print("\nStep 7: Deleting the 'hysteria' user...")
    run_command(["userdel", "-r", "hysteria"], "Failed to delete the 'hysteria' user.")

    print("\nStep 8: Removing cron jobs...")
    try:
        crontab_list_proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
        if "hysteria" in crontab_list_proc.stdout:
            new_crontab = "\n".join(line for line in crontab_list_proc.stdout.splitlines() if "hysteria" not in line)
            subprocess.run(["crontab", "-"], input=new_crontab.encode(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Hysteria cron jobs removed.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Warning: Could not access or modify crontab.")

    print("\nStep 9: Removing 'hys2' alias from .bashrc...")
    bashrc_path = os.path.expanduser("~/.bashrc")
    if os.path.exists(bashrc_path):
        try:
            with open(bashrc_path, 'r') as f_in:
                lines = [line for line in f_in if 'alias hys2=' not in line]
            with open(bashrc_path, 'w') as f_out:
                f_out.writelines(lines)
            print("Alias 'hys2' removed from .bashrc.")
        except IOError:
            print(f"Warning: Could not access or modify {bashrc_path}.")
    
    print("\nUninstallation of Hysteria2 panel is complete.")
    print("It is recommended to reboot the server to ensure all changes take effect.")
    
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This script must be run as root.")
        sys.exit(1)
    uninstall_hysteria()