import os
import subprocess
from enum import Enum
from datetime import datetime
import json
from typing import Any, Optional
from dotenv import dotenv_values
import re
import secrets
import string

import traffic

DEBUG = False

if os.name == 'nt' or not os.path.exists('/etc/hysteria'):
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    SCRIPT_DIR = os.path.join(BASE_DIR, 'core', 'scripts')
    CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
    CONFIG_ENV_FILE = os.path.join(BASE_DIR, '.configs.env')
    WEBPANEL_ENV_FILE = os.path.join(BASE_DIR, 'core', 'scripts', 'webpanel', '.env')
    NORMALSUB_ENV_FILE = os.path.join(BASE_DIR, 'core', 'scripts', 'normalsub', '.env')
    TELEGRAM_ENV_FILE = os.path.join(BASE_DIR, 'core', 'scripts', 'telegrambot', '.env')
    NODES_JSON_PATH = os.path.join(BASE_DIR, 'nodes.json')
else:
    SCRIPT_DIR = '/etc/hysteria/core/scripts'
    CONFIG_FILE = '/etc/hysteria/config.json'
    CONFIG_ENV_FILE = '/etc/hysteria/.configs.env'
    WEBPANEL_ENV_FILE = '/etc/hysteria/core/scripts/webpanel/.env'
    NORMALSUB_ENV_FILE = '/etc/hysteria/core/scripts/normalsub/.env'
    TELEGRAM_ENV_FILE = '/etc/hysteria/core/scripts/telegrambot/.env'
    NODES_JSON_PATH = "/etc/hysteria/nodes.json"


class Command(Enum):
    INSTALL_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'install.sh')
    UNINSTALL_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'uninstall.py')
    UPDATE_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'update.py')
    RESTART_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'restart.py')
    CHANGE_PORT_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'change_port.py')
    CHANGE_SNI_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'change_sni.py')
    GET_USER = os.path.join(SCRIPT_DIR, 'hysteria2', 'get_user.py')
    ADD_USER = os.path.join(SCRIPT_DIR, 'hysteria2', 'add_user.py')
    BULK_USER = os.path.join(SCRIPT_DIR, 'hysteria2', 'bulk_users.py')
    EDIT_USER = os.path.join(SCRIPT_DIR, 'hysteria2', 'edit_user.py')
    RESET_USER = os.path.join(SCRIPT_DIR, 'hysteria2', 'reset_user.py')
    REMOVE_USER = os.path.join(SCRIPT_DIR, 'hysteria2', 'remove_user.py')
    SHOW_USER_URI = os.path.join(SCRIPT_DIR, 'hysteria2', 'show_user_uri.py')
    WRAPPER_URI = os.path.join(SCRIPT_DIR, 'hysteria2', 'wrapper_uri.py')
    IP_ADD = os.path.join(SCRIPT_DIR, 'hysteria2', 'ip.py')
    NODE_MANAGER = os.path.join(SCRIPT_DIR, 'nodes', 'node.py')
    MANAGE_OBFS = os.path.join(SCRIPT_DIR, 'hysteria2', 'manage_obfs.py')
    MASQUERADE_SCRIPT = os.path.join(SCRIPT_DIR, 'hysteria2', 'masquerade.py')
    EXTRA_CONFIG_SCRIPT = os.path.join(SCRIPT_DIR, 'hysteria2', 'extra_config.py')
    TRAFFIC_STATUS = 'traffic.py'
    UPDATE_GEO = os.path.join(SCRIPT_DIR, 'hysteria2', 'update_geo.py')
    LIST_USERS = os.path.join(SCRIPT_DIR, 'hysteria2', 'list_users.py')
    SERVER_INFO = os.path.join(SCRIPT_DIR, 'hysteria2', 'server_info.py')
    BACKUP_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'backup.py')
    RESTORE_HYSTERIA2 = os.path.join(SCRIPT_DIR, 'hysteria2', 'restore.py')
    INSTALL_TELEGRAMBOT = os.path.join(SCRIPT_DIR, 'telegrambot', 'runbot.py')
    SHELL_SINGBOX = os.path.join(SCRIPT_DIR, 'singbox', 'singbox_shell.sh')
    SHELL_WEBPANEL = os.path.join(SCRIPT_DIR, 'webpanel', 'webpanel_shell.sh')
    INSTALL_NORMALSUB = os.path.join(SCRIPT_DIR, 'normalsub', 'normalsub.sh')
    INSTALL_TCP_BRUTAL = os.path.join(SCRIPT_DIR, 'tcp-brutal', 'install.py')
    INSTALL_WARP = os.path.join(SCRIPT_DIR, 'warp', 'install.py')
    UNINSTALL_WARP = os.path.join(SCRIPT_DIR, 'warp', 'uninstall.py')
    CONFIGURE_WARP = os.path.join(SCRIPT_DIR, 'warp', 'configure.py')
    STATUS_WARP = os.path.join(SCRIPT_DIR, 'warp', 'status.py')
    SERVICES_STATUS = os.path.join(SCRIPT_DIR, 'services_status.sh')
    VERSION = os.path.join(SCRIPT_DIR, 'hysteria2', 'version.py')
    LIMIT_SCRIPT = os.path.join(SCRIPT_DIR, 'hysteria2', 'limit.sh')
    KICK_USER_SCRIPT = os.path.join(SCRIPT_DIR, 'hysteria2', 'kickuser.py')




class HysteriaError(Exception):
    pass


class CommandExecutionError(HysteriaError):
    pass


class InvalidInputError(HysteriaError):
    pass


class PasswordGenerationError(HysteriaError):
    pass


class ScriptNotFoundError(HysteriaError):
    pass



def run_cmd(command: list[str]) -> str:
    if DEBUG:
        print(f"Executing command: {' '.join(command)}")
    try:
        process = subprocess.run(command, capture_output=True, text=True, shell=False, check=False)

        if process.returncode != 0:
            error_output = process.stderr.strip() if process.stderr.strip() else process.stdout.strip()
            if not error_output:
                error_output = f"Command exited with status {process.returncode} without specific error message."
            
            detailed_error_message = f"Command '{' '.join(command)}' failed with exit code {process.returncode}: {error_output}"
            raise CommandExecutionError(detailed_error_message)

        return process.stdout.strip() if process.stdout else ""

    except FileNotFoundError as e:
        raise ScriptNotFoundError(f"Script or command not found: {command[0]}. Original error: {e}")
    except subprocess.TimeoutExpired as e: 
        raise CommandExecutionError(f"Command '{' '.join(command)}' timed out. Original error: {e}")
    except OSError as e: 
        raise CommandExecutionError(f"OS error while trying to run command '{' '.join(command)}': {e}")


def run_cmd_and_stream(command: list[str]):
    if DEBUG:
        print(f"Executing command: {' '.join(command)}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
            process.stdout.close()
        
        return_code = process.wait()

        if return_code != 0:
            raise CommandExecutionError(f"Process failed with exit code {return_code}")

    except FileNotFoundError as e:
        raise ScriptNotFoundError(f"Script or command not found: {command[0]}. Original error: {e}")
    except OSError as e: 
        raise CommandExecutionError(f"OS error while trying to run command '{' '.join(command)}': {e}")


def generate_password() -> str:
    try:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    except Exception as e:
        raise PasswordGenerationError(f"Failed to generate password using secrets module: {e}")





def install_hysteria2(port: int, sni: str):
    run_cmd_and_stream(['bash', Command.INSTALL_HYSTERIA2.value, str(port), sni])
    run_cmd(['python3', Command.IP_ADD.value, 'add'])


def uninstall_hysteria2():
    run_cmd(['python3', Command.UNINSTALL_HYSTERIA2.value])


def update_hysteria2():
    run_cmd(['python3', Command.UPDATE_HYSTERIA2.value])


def restart_hysteria2():
    run_cmd(['python3', Command.RESTART_HYSTERIA2.value])


def get_hysteria2_port() -> int | None:
    config = get_hysteria2_config_file()
    port = config['listen'].split(':')
    if len(port) > 1:
        return int(port[1])
    return None


def change_hysteria2_port(port: int):
    run_cmd(['python3', Command.CHANGE_PORT_HYSTERIA2.value, str(port)])


def get_hysteria2_sni() -> str | None:
    env_vars = dotenv_values(CONFIG_ENV_FILE)
    return env_vars.get('SNI')


def change_hysteria2_sni(sni: str):
    run_cmd(['python3', Command.CHANGE_SNI_HYSTERIA2.value, sni])


def backup_hysteria2():
    try:
        run_cmd(['python3', Command.BACKUP_HYSTERIA2.value])
    except subprocess.CalledProcessError as e:
        raise Exception(f"Backup failed: {e}")
    except Exception as ex:
        raise


def restore_hysteria2(backup_file_path: str):
    try:
        run_cmd(['python3', Command.RESTORE_HYSTERIA2.value, backup_file_path])
    except subprocess.CalledProcessError as e:
        raise Exception(f"Restore failed: {e}")
    except Exception as ex:
        raise


def enable_hysteria2_obfs():
    run_cmd(['python3', Command.MANAGE_OBFS.value, '--generate'])


def disable_hysteria2_obfs():
    run_cmd(['python3', Command.MANAGE_OBFS.value, '--remove'])

def check_hysteria2_obfs():
    result = subprocess.run(["python3", Command.MANAGE_OBFS.value, "--check"], check=True, capture_output=True, text=True)
    return result.stdout.strip()

def enable_hysteria2_masquerade():
    return run_cmd(['python3', Command.MASQUERADE_SCRIPT.value, '1'])

def disable_hysteria2_masquerade():
    return run_cmd(['python3', Command.MASQUERADE_SCRIPT.value, '2'])

def get_hysteria2_masquerade_status():
    return run_cmd(['python3', Command.MASQUERADE_SCRIPT.value, 'status'])


def get_hysteria2_config_file() -> dict[str, Any]:
    with open(CONFIG_FILE, 'r') as f:
        return json.loads(f.read())


def set_hysteria2_config_file(data: dict[str, Any]):
    content = json.dumps(data, indent=4)

    with open(CONFIG_FILE, 'w') as f:
        f.write(content)



def list_users() -> dict[str, dict[str, Any]] | None:
    if res := run_cmd(['python3', Command.LIST_USERS.value]):
        return json.loads(res)


def get_user(username: str) -> dict[str, Any] | None:
    if res := run_cmd(['python3', Command.GET_USER.value, '-u', str(username)]):
        return json.loads(res)


def add_user(username: str, traffic_limit: int, expiration_days: int, password: str | None, creation_date: str | None, unlimited: bool, note: str | None):
    command = ['python3', Command.ADD_USER.value, username, str(traffic_limit), str(expiration_days)]

    final_password = password if password else generate_password()
    command.append(final_password)
    
    if unlimited:
        command.append('true')
    
    if note:
        if not unlimited: command.append('false')
        command.append(note)
    
    if creation_date:
        if not unlimited: command.append('false')
        if not note: command.append('')
        command.append(creation_date)
        
    run_cmd(command)

def bulk_user_add(traffic_gb: float, expiration_days: int, count: int, prefix: str, start_number: int, unlimited: bool):
    command = [
        'python3', 
        Command.BULK_USER.value,
        '--traffic-gb', str(traffic_gb),
        '--expiration-days', str(expiration_days),
        '--count', str(count),
        '--prefix', prefix,
        '--start-number', str(start_number)
    ]

    if unlimited:
        command.append('--unlimited')
        
    run_cmd(command)

def edit_user(username: str, new_username: str | None, new_password: str | None, new_traffic_limit: int | None, new_expiration_days: int | None, renew_password: bool, renew_creation_date: bool, blocked: bool | None, unlimited_ip: bool | None, note: str | None):
    if not username:
        raise InvalidInputError('Error: username is required')

    command_args = ['python3', Command.EDIT_USER.value, username]

    if new_username:
        command_args.extend(['--new-username', new_username])

    password_to_set = None
    if new_password:
        password_to_set = new_password
    elif renew_password:
        password_to_set = generate_password()

    if password_to_set:
        command_args.extend(['--password', password_to_set])

    if new_traffic_limit is not None:
        if new_traffic_limit < 0:
            raise InvalidInputError('Error: traffic limit must be a non-negative number.')
        command_args.extend(['--traffic-gb', str(new_traffic_limit)])

    if new_expiration_days is not None:
        if new_expiration_days < 0:
            raise InvalidInputError('Error: expiration days must be a non-negative number.')
        command_args.extend(['--expiration-days', str(new_expiration_days)])
        
    if renew_creation_date:
        creation_date = datetime.now().strftime('%Y-%m-%d')
        command_args.extend(['--creation-date', creation_date])
        
    if blocked is not None:
        command_args.extend(['--blocked', 'true' if blocked else 'false'])
        
    if unlimited_ip is not None:
        command_args.extend(['--unlimited', 'true' if unlimited_ip else 'false'])

    if note is not None:
        command_args.extend(['--note', note])

    run_cmd(command_args)


def reset_user(username: str):
    run_cmd(['python3', Command.RESET_USER.value, username])


def remove_users(usernames: list[str]):
    if not usernames:
        return
    run_cmd(['python3', Command.REMOVE_USER.value, *usernames])

def kick_users_by_name(usernames: list[str]):
    if not usernames:
        raise InvalidInputError('Username(s) must be provided to kick.')
    script_path = Command.KICK_USER_SCRIPT.value
    if not os.path.exists(script_path):
        raise ScriptNotFoundError(f"Kick user script not found at: {script_path}")
    try:
        subprocess.run(['python3', script_path, *usernames], check=True)
    except subprocess.CalledProcessError as e:
        raise CommandExecutionError(f"Failed to execute kick user script: {e}")
        
def show_user_uri(username: str, qrcode: bool, ipv: int, all: bool, singbox: bool, normalsub: bool) -> str | None:
    command_args = ['python3', Command.SHOW_USER_URI.value, '-u', username]
    if qrcode:
        command_args.append('-qr')
    if all:
        command_args.append('-a')
    else:
        command_args.extend(['-ip', str(ipv)])
    if singbox:
        command_args.append('-s')
    if normalsub:
        command_args.append('-n')
    return run_cmd(command_args)

def show_user_uri_json(usernames: list[str]) -> list[dict[str, Any]] | None:
    script_path = Command.WRAPPER_URI.value
    if not os.path.exists(script_path):
        raise ScriptNotFoundError(f"Wrapper URI script not found at: {script_path}")
    try:
        process = subprocess.run(['python3', script_path, *usernames], capture_output=True, text=True, check=True)
        return json.loads(process.stdout)
    except subprocess.CalledProcessError as e:
        raise CommandExecutionError(f"Failed to execute wrapper URI script: {e}\nError: {e.stderr}")
    except FileNotFoundError:
        raise ScriptNotFoundError(f'Script not found: {script_path}')
    except json.JSONDecodeError:
        raise CommandExecutionError(f"Failed to decode JSON output from script: {script_path}\nOutput: {process.stdout if 'process' in locals() else 'No output'}")
    except Exception as e:
        raise HysteriaError(f'An unexpected error occurred: {e}')
        



def traffic_status(no_gui=False, display_output=True):
    if no_gui:
        data = traffic.traffic_status(no_gui=True)
        traffic.kick_expired_users()
    else:
        data = traffic.traffic_status(no_gui=True if not display_output else no_gui)
    
    return data


def server_info() -> str | None:
    return run_cmd(['python3', Command.SERVER_INFO.value])


def get_ip_address() -> tuple[str | None, str | None]:
    env_vars = dotenv_values(CONFIG_ENV_FILE)

    return env_vars.get('IP4'), env_vars.get('IP6')


def add_ip_address():
    run_cmd(['python3', Command.IP_ADD.value, 'add'])


def edit_ip_address(ipv4: str, ipv6: str):

    if ipv4:
        run_cmd(['python3', Command.IP_ADD.value, 'edit', '-4', ipv4])
    if ipv6:
        run_cmd(['python3', Command.IP_ADD.value, 'edit', '-6', ipv6])

def add_node(name: str, ip: str, sni: Optional[str] = None, pinSHA256: Optional[str] = None, port: Optional[int] = None, obfs: Optional[str] = None, insecure: Optional[bool] = None, location: Optional[str] = None):
    command = ['python3', Command.NODE_MANAGER.value, 'add', '--name', name, '--ip', ip]
    if port:
        command.extend(['--port', str(port)])
    if sni:
        command.extend(['--sni', sni])
    if pinSHA256:
        command.extend(['--pinSHA256', pinSHA256])
    if obfs:
        command.extend(['--obfs', obfs])
    if insecure:
        command.append('--insecure')
    if location:
        command.extend(['--location', location])
    return run_cmd(command)

def edit_node(name: str, new_name: Optional[str] = None, ip: Optional[str] = None, sni: Optional[str] = None, pinSHA256: Optional[str] = None, port: Optional[int] = None, obfs: Optional[str] = None, insecure: Optional[bool] = None, location: Optional[str] = None):
    command = ['python3', Command.NODE_MANAGER.value, 'edit', '--name', name]
    if new_name:
        command.extend(['--new-name', new_name])
    if ip:
        command.extend(['--ip', ip])
    if port:
        command.extend(['--port', str(port)])
    if sni:
        command.extend(['--sni', sni])
    if pinSHA256:
        command.extend(['--pinSHA256', pinSHA256])
    if obfs:
        command.extend(['--obfs', obfs])
    if insecure is not None:
        if insecure:
            command.append('--insecure')
        else:
            command.append('--secure')
    if location:
        command.extend(['--location', location])
    return run_cmd(command)

def delete_node(name: str):
    return run_cmd(['python3', Command.NODE_MANAGER.value, 'delete', '--name', name])

def list_nodes():
    return run_cmd(['python3', Command.NODE_MANAGER.value, 'list'])

def generate_node_cert():
    return run_cmd(['python3', Command.NODE_MANAGER.value, 'generate-cert'])

def update_geo(country: str):
    script_path = Command.UPDATE_GEO.value
    try:
        subprocess.run(['python3', script_path, country.lower()], check=True)
    except subprocess.CalledProcessError as e:
        raise CommandExecutionError(f'Failed to update geo files: {e}')
    except FileNotFoundError:
        raise ScriptNotFoundError(f'Script not found: {script_path}')
    except Exception as e:
        raise HysteriaError(f'An unexpected error occurred: {e}')

def add_extra_config(name: str, uri: str) -> str:
    return run_cmd(['python3', Command.EXTRA_CONFIG_SCRIPT.value, 'add', '--name', name, '--uri', uri])


def delete_extra_config(name: str) -> str:
    return run_cmd(['python3', Command.EXTRA_CONFIG_SCRIPT.value, 'delete', '--name', name])


def edit_extra_config(name: str, new_name: str = None, new_uri: str = None, enabled: bool = None) -> str:
    cmd = ['python3', Command.EXTRA_CONFIG_SCRIPT.value, 'edit', '--name', name]
    if new_name:
        cmd.extend(['--new-name', new_name])
    if new_uri:
        cmd.extend(['--uri', new_uri])
    if enabled is not None:
        cmd.extend(['--enabled', str(enabled).lower()])
    return run_cmd(cmd)


def list_extra_configs() -> str:
    return run_cmd(['python3', Command.EXTRA_CONFIG_SCRIPT.value, 'list'])


def get_extra_config(name: str) -> dict[str, Any] | None:
    if res := run_cmd(['python3', Command.EXTRA_CONFIG_SCRIPT.value, 'get', '--name', name]):
        return json.loads(res)




def install_tcp_brutal():
    run_cmd(['python3', Command.INSTALL_TCP_BRUTAL.value])


def install_warp():
    run_cmd(['python3', Command.INSTALL_WARP.value])


def uninstall_warp():
    run_cmd(['python3', Command.UNINSTALL_WARP.value])


def configure_warp(all_state: str | None = None, 
                   popular_sites_state: str | None = None, 
                   domestic_sites_state: str | None = None, 
                   block_adult_sites_state: str | None = None):
    cmd_args = [
        'python3', Command.CONFIGURE_WARP.value
    ]
    if all_state:
        cmd_args.extend(['--set-all', all_state])
    if popular_sites_state:
        cmd_args.extend(['--set-popular-sites', popular_sites_state])
    if domestic_sites_state:
        cmd_args.extend(['--set-domestic-sites', domestic_sites_state])
    if block_adult_sites_state:
        cmd_args.extend(['--set-block-adult', block_adult_sites_state])

    if len(cmd_args) == 2: 
        print("No WARP configuration options provided to cli_api.configure_warp.")
        return 

    run_cmd(cmd_args)


def warp_status() -> str | None:
    return run_cmd(['python3', Command.STATUS_WARP.value])


def start_telegram_bot(token: str, adminid: str, backup_interval: Optional[int] = None):
    if not token or not adminid:
        raise InvalidInputError('Error: Both --token and --adminid are required for the start action.')
    
    command = ['python3', Command.INSTALL_TELEGRAMBOT.value, 'start', token, adminid]
    if backup_interval is not None:
        command.append(str(backup_interval))
    
    run_cmd(command)

def stop_telegram_bot():
    run_cmd(['python3', Command.INSTALL_TELEGRAMBOT.value, 'stop'])

def get_telegram_bot_info() -> dict[str, Any]:
    try:
        output = run_cmd(['python3', Command.INSTALL_TELEGRAMBOT.value, 'info'])
        if output:
            return json.loads(output)
        return {}
    except Exception as e:
        print(f"Error getting telegram bot info: {e}")
        return {}

def get_telegram_bot_backup_interval() -> int | None:
    try:
        if not os.path.exists(TELEGRAM_ENV_FILE):
            return None 
        
        env_vars = dotenv_values(TELEGRAM_ENV_FILE)
        interval_str = env_vars.get('BACKUP_INTERVAL_HOUR')
        
        if interval_str:
            try:
                return int(float(interval_str))
            except (ValueError, TypeError):
                return None
        
        return None
    except Exception as e:
        print(f"Error reading Telegram Bot .env file: {e}")
        return None

def set_telegram_bot_backup_interval(backup_interval: int):
    if backup_interval is None:
        raise InvalidInputError('Error: Backup interval is required.')
    run_cmd(['python3', Command.INSTALL_TELEGRAMBOT.value, 'set_backup_interval', str(backup_interval)])


def start_singbox(domain: str, port: int):
    if not domain or not port:
        raise InvalidInputError('Error: Both --domain and --port are required for the start action.')
    run_cmd(['bash', Command.SHELL_SINGBOX.value, 'start', domain, str(port)])


def stop_singbox():
    run_cmd(['bash', Command.SHELL_SINGBOX.value, 'stop'])


def start_normalsub(domain: str, port: int):
    if not domain or not port:
        raise InvalidInputError('Error: Both --domain and --port are required for the start action.')
    run_cmd(['bash', Command.INSTALL_NORMALSUB.value, 'start', domain, str(port)])

def edit_normalsub_subpath(new_subpath: str):
    if not new_subpath:
        raise InvalidInputError('Error: New subpath cannot be empty.')
    if not re.match(r"^[a-zA-Z0-9]+(?:/[a-zA-Z0-9]+)*$", new_subpath):
        raise InvalidInputError("Error: Invalid subpath format. Must be alphanumeric segments separated by single slashes (e.g., 'path' or 'path/to/resource').")
    
    run_cmd(['bash', Command.INSTALL_NORMALSUB.value, 'edit_subpath', new_subpath])

def edit_normalsub_profile_title(new_title: str):
    if not new_title:
        raise InvalidInputError('Error: New profile title cannot be empty.')
    
    run_cmd(['bash', Command.INSTALL_NORMALSUB.value, 'edit_profile_title', new_title])

def edit_normalsub_support_url(new_url: str):
    run_cmd(['bash', Command.INSTALL_NORMALSUB.value, 'edit_support_url', new_url if new_url else ""])

def edit_normalsub_show_username(enabled: bool):
    val = "true" if enabled else "false"
    run_cmd(['bash', Command.INSTALL_NORMALSUB.value, 'edit_show_username', val])

def get_normalsub_show_username() -> bool:
    try:
        if not os.path.exists(NORMALSUB_ENV_FILE):
            return True 
        
        env_vars = dotenv_values(NORMALSUB_ENV_FILE)
        return env_vars.get('SHOW_USERNAME', 'true').lower() == 'true'
    except Exception as e:
        print(f"Error reading NormalSub .env file: {e}")
        return True

def get_normalsub_profile_title() -> str:
    try:
        if not os.path.exists(NORMALSUB_ENV_FILE):
            return 'ANY' 
        
        env_vars = dotenv_values(NORMALSUB_ENV_FILE)
        return env_vars.get('PROFILE_TITLE', 'ANY')
    except Exception as e:
        print(f"Error reading NormalSub .env file: {e}")
        return 'ANY'

def get_normalsub_support_url() -> str:
    try:
        if not os.path.exists(NORMALSUB_ENV_FILE):
            return '' 
        
        env_vars = dotenv_values(NORMALSUB_ENV_FILE)
        return env_vars.get('SUPPORT_URL', '')
    except Exception as e:
        print(f"Error reading NormalSub .env file: {e}")
        return ''

def get_normalsub_subpath() -> str | None:
    try:
        if not os.path.exists(NORMALSUB_ENV_FILE):
            return None 
        
        env_vars = dotenv_values(NORMALSUB_ENV_FILE)
        return env_vars.get('SUBPATH')
    except Exception as e:
        print(f"Error reading NormalSub .env file: {e}")
        return None

def stop_normalsub():
    run_cmd(['bash', Command.INSTALL_NORMALSUB.value, 'stop'])


def start_webpanel(domain: str, port: int, admin_username: str, admin_password: str, expiration_minutes: int, debug: bool, decoy_path: str, self_signed: bool):
    if not domain or not port or not admin_username or not admin_password or not expiration_minutes:
        raise InvalidInputError('Error: Both --domain and --port are required for the start action.')
    run_cmd(
        ['bash', Command.SHELL_WEBPANEL.value, 'start',
         domain, str(port), admin_username, admin_password, str(expiration_minutes), str(debug).lower(), str(decoy_path), str(self_signed).lower()]
    )


def stop_webpanel():
    run_cmd(['bash', Command.SHELL_WEBPANEL.value, 'stop'])

def setup_webpanel_decoy(domain: str, decoy_path: str):
    if not domain or not decoy_path:
        raise InvalidInputError('Error: Both domain and decoy_path are required.')
    run_cmd(['bash', Command.SHELL_WEBPANEL.value, 'decoy', domain, decoy_path])

def stop_webpanel_decoy():
    run_cmd(['bash', Command.SHELL_WEBPANEL.value, 'stopdecoy'])

def get_webpanel_decoy_status() -> dict[str, Any]:
    try:
        if not os.path.exists(WEBPANEL_ENV_FILE):
            return {"active": False, "path": None}

        env_vars = dotenv_values(WEBPANEL_ENV_FILE)
        decoy_path = env_vars.get('DECOY_PATH')

        if decoy_path and decoy_path.strip():
            return {"active": True, "path": decoy_path.strip()}
        else:
            return {"active": False, "path": None}
    except Exception as e:
        print(f"Error checking decoy status: {e}")
        return {"active": False, "path": None}

def get_webpanel_url() -> str | None:
    return run_cmd(['bash', Command.SHELL_WEBPANEL.value, 'url'])


def get_webpanel_api_token() -> str | None:
    return run_cmd(['bash', Command.SHELL_WEBPANEL.value, 'api-token'])

def get_webpanel_env_config() -> dict[str, Any]:
    try:
        if not os.path.exists(WEBPANEL_ENV_FILE):
            return {}
        
        env_vars = dotenv_values(WEBPANEL_ENV_FILE)
        config = {}

        config['DOMAIN'] = env_vars.get('DOMAIN')
        config['ROOT_PATH'] = env_vars.get('ROOT_PATH')
        
        port_val = env_vars.get('PORT')
        if port_val and port_val.isdigit():
            config['PORT'] = int(port_val)
        
        exp_val = env_vars.get('EXPIRATION_MINUTES')
        if exp_val and exp_val.isdigit():
            config['EXPIRATION_MINUTES'] = int(exp_val)
        
        auth_val = env_vars.get('TELEGRAM_AUTH_ENABLED')
        config['TELEGRAM_AUTH_ENABLED'] = (auth_val == 'true')
            
        return config
    except Exception as e:
        print(f"Error reading WebPanel .env file: {e}")
        return {}

def reset_webpanel_credentials(new_username: str | None = None, new_password: str | None = None):
    if not new_username and not new_password:
        raise InvalidInputError('Error: At least new username or new password must be provided.')

    cmd_args = ['bash', Command.SHELL_WEBPANEL.value, 'resetcreds']
    if new_username:
        cmd_args.extend(['-u', new_username])
    if new_password:
        cmd_args.extend(['-p', new_password])
    
    run_cmd(cmd_args)

def set_webpanel_telegram_auth(enabled: bool):
    val = 'true' if enabled else 'false'
    run_cmd(
        ['bash', Command.SHELL_WEBPANEL.value, 'settelegramauth', val]
    )

def change_webpanel_expiration(expiration_minutes: int):
    if not expiration_minutes:
        raise InvalidInputError('Error: Expiration minutes must be provided.')
    run_cmd(
        ['bash', Command.SHELL_WEBPANEL.value, 'changeexp', str(expiration_minutes)]
    )


def change_webpanel_root_path(root_path: str | None = None):
    cmd_args = ['bash', Command.SHELL_WEBPANEL.value, 'changeroot']
    if root_path:
        cmd_args.append(root_path)
    run_cmd(cmd_args)


def change_webpanel_domain_port(domain: str | None = None, port: int | None = None):
    if not domain and not port:
        raise InvalidInputError('Error: At least a new domain or new port must be provided.')
    
    cmd_args = ['bash', Command.SHELL_WEBPANEL.value, 'changedomain']
    if domain:
        cmd_args.extend(['-d', domain])
    if port:
        cmd_args.extend(['-p', str(port)])
    
    run_cmd(cmd_args)

def get_services_status() -> dict[str, bool] | None:
    if res := run_cmd(['bash', Command.SERVICES_STATUS.value]):
        return json.loads(res)

def show_version() -> str | None:
    return run_cmd(['python3', Command.VERSION.value, 'show-version'])


def check_version() -> str | None:
    return run_cmd(['python3', Command.VERSION.value, 'check-version'])

def start_ip_limiter():
    run_cmd(['bash', Command.LIMIT_SCRIPT.value, 'start'])

def stop_ip_limiter():
    run_cmd(['bash', Command.LIMIT_SCRIPT.value, 'stop'])

def clean_ip_limiter():
    run_cmd(['bash', Command.LIMIT_SCRIPT.value, 'clean'])

def config_ip_limiter(block_duration: Optional[int] = None, max_ips: Optional[int] = None):
    if block_duration is not None and block_duration <= 0:
        raise InvalidInputError("Block duration must be greater than 0.")
    if max_ips is not None and max_ips <= 0:
        raise InvalidInputError("Max IPs must be greater than 0.")

    cmd_args = ['bash', Command.LIMIT_SCRIPT.value, 'config']
    if block_duration is not None:
        cmd_args.append(str(block_duration))
    else:
        cmd_args.append('')

    if max_ips is not None:
        cmd_args.append(str(max_ips))
    else:
        cmd_args.append('')

    run_cmd(cmd_args)

def get_ip_limiter_config() -> dict[str, int | None]:
    try:
        if not os.path.exists(CONFIG_ENV_FILE):
            return {"block_duration": None, "max_ips": None}
        
        env_vars = dotenv_values(CONFIG_ENV_FILE)
        block_duration_str = env_vars.get('BLOCK_DURATION')
        max_ips_str = env_vars.get('MAX_IPS')
        
        block_duration = int(block_duration_str) if block_duration_str and block_duration_str.isdigit() else None
        max_ips = int(max_ips_str) if max_ips_str and max_ips_str.isdigit() else None
            
        return {"block_duration": block_duration, "max_ips": max_ips}
    except Exception as e:
        print(f"Error reading IP Limiter config from .configs.env: {e}")
        return {"block_duration": None, "max_ips": None}

def change_webpanel_root_path(new_path: str):
    run_cmd(['bash', Command.WEBPANEL_SCRIPT.value, 'changeroot', new_path])

def get_webpanel_root_path() -> str:
    config = get_webpanel_env_config()
    return config.get('ROOT_PATH', '')
