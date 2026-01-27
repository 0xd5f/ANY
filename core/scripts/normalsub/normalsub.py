import os
import json
import subprocess
import re
import time
import shlex
import base64
import sys
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from io import BytesIO

from aiohttp import web
from aiohttp.web_middlewares import middleware
from urllib.parse import unquote, parse_qs, urlparse, urljoin, quote
from dotenv import load_dotenv
import qrcode
from jinja2 import Environment, FileSystemLoader

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from db.database import db

load_dotenv()


@dataclass
class AppConfig:
    domain: str
    external_port: int
    aiohttp_listen_address: str
    aiohttp_listen_port: int
    sni_file: str
    singbox_template_path: str
    hysteria_cli_path: str
    nodes_json_path: str
    extra_config_path: str
    rate_limit: int
    rate_limit_window: int
    sni: str
    template_dir: str
    subpath: str
    profile_title: str
    show_username: bool
    support_url: str



class RateLimiter:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.store: Dict[str, Tuple[int, float]] = {}

    def check_limit(self, client_ip: str) -> bool:
        current_time = time.monotonic()
        requests, last_request_time = self.store.get(client_ip, (0, 0))
        if current_time - last_request_time < self.window:
            if requests >= self.limit:
                return False
        else:
            requests = 0
        self.store[client_ip] = (requests + 1, current_time)
        return True


@dataclass
class UriComponents:
    username: Optional[str]
    password: Optional[str]
    ip: Optional[str]
    port: Optional[int]
    obfs_password: str


@dataclass
class UserInfo:
    username: str
    password: str
    upload_bytes: int
    download_bytes: int
    max_download_bytes: int
    account_creation_date: str
    expiration_days: int
    blocked: bool = False

    @property
    def total_usage(self) -> int:
        return self.upload_bytes + self.download_bytes

    @property
    def expiration_timestamp(self) -> int:
        if not self.account_creation_date or self.expiration_days <= 0:
            return 0
        creation_timestamp = int(time.mktime(time.strptime(self.account_creation_date, "%Y-%m-%d")))
        return creation_timestamp + (self.expiration_days * 24 * 3600)

    @property
    def expiration_date(self) -> str:
        if not self.account_creation_date:
            return "N/A"
        if self.expiration_days <= 0:
            return "Unlimited"
        creation_timestamp = int(time.mktime(time.strptime(self.account_creation_date, "%Y-%m-%d")))
        expiration_timestamp = creation_timestamp + (self.expiration_days * 24 * 3600)
        return time.strftime("%Y-%m-%d", time.localtime(expiration_timestamp))

    @property
    def usage_human_readable(self) -> str:
        used = Utils.human_readable_bytes(self.total_usage)
        if self.max_download_bytes > 0:
            total = Utils.human_readable_bytes(self.max_download_bytes)
            return f"{used} / {total}"
        else:
            return f"{used} / Unlimited"

    @property
    def usage_detailed(self) -> str:
        if self.max_download_bytes > 0:
            total = Utils.human_readable_bytes(self.max_download_bytes)
        else:
            total = "Unlimited"
        upload = Utils.human_readable_bytes(self.upload_bytes)
        download = Utils.human_readable_bytes(self.download_bytes)
        return f"Upload: {upload}, Download: {download}, Total: {total}"


@dataclass
class NodeURI:
    label: str
    uri: str
    qrcode: Optional[str] = None


@dataclass
class TemplateContext:
    username: str
    usage: str
    usage_raw: str
    expiration_date: str
    days_remaining: int
    status: str
    sublink_qrcode: str
    sub_link: str
    sub_link_encoded: str
    profile_title_encoded: str
    blocked: bool = False
    local_uris: List[NodeURI] = field(default_factory=list)
    node_uris: List[NodeURI] = field(default_factory=list)
    singbox_qrcode: Optional[str] = None
    hiddify_qrcode: Optional[str] = None
    streisand_qrcode: Optional[str] = None
    nekobox_qrcode: Optional[str] = None


class Utils:
    @staticmethod
    def sanitize_input(value: str, pattern: str) -> str:
        if not re.match(pattern, value):
            raise ValueError(f"Invalid value: {value}")
        return shlex.quote(value)

    @staticmethod
    def generate_qrcode_base64(data: str) -> str:
        if not data:
            return None
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

    @staticmethod
    def human_readable_bytes(bytes_value: int) -> str:
        units = ["Bytes", "KB", "MB", "GB", "TB"]
        size = float(bytes_value)
        for unit in units:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    @staticmethod
    def build_url(base: str, path: str) -> str:
        return urljoin(base, path)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False


class HysteriaCLI:
    def __init__(self, cli_path: str):
        self.cli_path = cli_path

    def _run_command(self, args: List[str]) -> str:
        try:
            command = ['python3', self.cli_path] + args
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                if "User not found" in stderr:
                    return None
                else:
                    print(f"Hysteria CLI error: {stderr}")
                    raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)
            return stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Hysteria CLI error: {e}")
            raise

    def get_username_by_password(self, password_token: str) -> Optional[str]:
        if not db:
            return None
        user_doc = db.collection.find_one({"password": password_token}, {"_id": 1})
        return user_doc['_id'] if user_doc else None

    def get_user_info(self, username: str) -> Optional[UserInfo]:
        if not db:
            return None
        user_doc = db.get_user(username)
        if not user_doc:
            return None
        
        return UserInfo(
            username=user_doc.get('_id'),
            password=user_doc.get('password'),
            upload_bytes=user_doc.get('upload_bytes', 0),
            download_bytes=user_doc.get('download_bytes', 0),
            max_download_bytes=user_doc.get('max_download_bytes', 0),
            account_creation_date=user_doc.get('account_creation_date', ''),
            expiration_days=user_doc.get('expiration_days', 0),
            blocked=user_doc.get('blocked', False)
        )

    def get_all_uris(self, username: str) -> List[str]:
        output = self._run_command(['show-user-uri', '-u', username, '-a'])
        if not output:
            return []
        return re.findall(r'hy2://.*', output)

    def get_all_labeled_uris(self, username: str) -> List[Dict[str, str]]:
        output = self._run_command(['show-user-uri', '-u', username, '-a'])
        if not output:
            return []
        
        matches = re.findall(r"^(.*?):\s*(hy2://.*)$", output, re.MULTILINE)
        return [{'label': label.strip(), 'uri': uri} for label, uri in matches]


class UriParser:
    @staticmethod
    def extract_uri_components(uri: Optional[str], prefix: str) -> Optional[UriComponents]:
        if not uri or not uri.startswith(prefix):
            return None
        uri = uri[len(prefix):].strip()
        try:
            decoded_uri = unquote(uri)
            parsed_url = urlparse(decoded_uri)
            query_params = parse_qs(parsed_url.query)
            hostname = parsed_url.hostname
            if hostname and hostname.startswith('[') and hostname.endswith(']'):
                hostname = hostname[1:-1]
            port = parsed_url.port if parsed_url.port is not None else None
            return UriComponents(
                username=parsed_url.username,
                password=parsed_url.password,
                ip=hostname,
                port=port,
                obfs_password=query_params.get('obfs-password', [''])[0]
            )
        except Exception as e:
            print(f"Error during URI parsing: {e}, URI: {uri}")
            return None


class SingboxConfigGenerator:
    def __init__(self, hysteria_cli: HysteriaCLI, default_sni: str):
        self.hysteria_cli = hysteria_cli
        self.default_sni = default_sni
        self._template_cache = None
        self.template_path = None

    def set_template_path(self, path: str):
        self.template_path = path
        self._template_cache = None

    def get_template(self) -> Dict[str, Any]:
        if self._template_cache is None:
            try:
                with open(self.template_path, 'r') as f:
                    self._template_cache = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
                raise RuntimeError(f"Error loading Singbox template: {e}") from e
        return self._template_cache.copy()

    def generate_config_from_uri(self, uri: str, username: str, fragment: str) -> Optional[Dict[str, Any]]:
        if not uri:
            return None

        try:
            parsed_url = urlparse(uri)
            server = parsed_url.hostname
            server_port = parsed_url.port
            auth_password = parsed_url.password
            auth_user = unquote(parsed_url.username or '')
            obfs_password = parse_qs(parsed_url.query).get('obfs-password', [''])[0]
            
            if auth_password:
                if auth_user:
                    final_password = f"{auth_user}:{auth_password}"
                else:
                    final_password = auth_password
            else:
                final_password = auth_user
                
        except Exception as e:
            print(f"Error during Singbox config generation from URI: {e}, URI: {uri}")
            return None

        outbound_config = {
            "type": "hysteria2",
            "tag": unquote(parsed_url.fragment), 
            "server": server,
            "server_port": server_port,
            "password": final_password,
            "tls": {
                "enabled": True,
                "server_name": fragment if fragment else self.default_sni,
                "insecure": True
            }
        }

        if obfs_password:
            outbound_config["obfs"] = {
                "type": "salamander",
                "password": obfs_password
            }

        return outbound_config

    def combine_configs(self, all_uris: List[str], username: str, fragment: str) -> Optional[Dict[str, Any]]:
        if not all_uris:
            return None
        
        combined_config = self.get_template()
        combined_config['outbounds'] = [out for out in combined_config['outbounds'] if out.get('type') != 'hysteria2']

        hysteria_outbounds = []
        for uri in all_uris:
            outbound = self.generate_config_from_uri(uri, username, fragment)
            if outbound:
                hysteria_outbounds.append(outbound)

        if not hysteria_outbounds:
            return None

        all_tags = [out['tag'] for out in hysteria_outbounds]

        for outbound in combined_config['outbounds']:
            if outbound.get('tag') == 'select':
                outbound['outbounds'] = ["auto"] + all_tags
            elif outbound.get('tag') == 'auto':
                outbound['outbounds'] = all_tags

        combined_config['outbounds'].extend(hysteria_outbounds)
        return combined_config


class SubscriptionManager:
    def __init__(self, hysteria_cli: HysteriaCLI, config: AppConfig):
        self.hysteria_cli = hysteria_cli
        self.config = config

    def _get_extra_configs(self) -> List[str]:
        if not os.path.exists(self.config.extra_config_path):
            return []
        try:
            with open(self.config.extra_config_path, 'r') as f:
                content = f.read()
                if not content:
                    return []
                configs = json.loads(content)
                if isinstance(configs, list):
                    cleaned_uris = []
                    for c in configs:
                        is_enabled = c.get('enabled', True)
                        if 'uri' in c and is_enabled:
                            uri = str(c['uri']).replace('%20%5B%2ACIDR%5D', '')
                            
                            if 'name' in c and c['name']:
                                try:
                                    if '#' in uri:
                                        base_uri = uri.split('#')[0]
                                    else:
                                        base_uri = uri
                                    
                                    new_name = quote(str(c['name']))
                                    uri = f"{base_uri}#{new_name}"
                                except Exception as e:
                                    print(f"Error applying name override: {e}")

                            cleaned_uris.append(uri)
                    return cleaned_uris
                return []
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Warning: Could not read or parse extra configs from {self.config.extra_config_path}: {e}")
            return []

    def get_normal_subscription(self, username: str, user_agent: str) -> str:
        user_info = self.hysteria_cli.get_user_info(username)
        if user_info is None:
            return "User not found"
            
        all_uris = self.hysteria_cli.get_all_uris(username)

        processed_uris = []
        for uri in all_uris:
            if "v2ray" in user_agent and "ng" in user_agent:
                match = re.search(r'pinSHA256=sha256/([^&]+)', uri)
                if match:
                    decoded = base64.b64decode(match.group(1))
                    formatted = ":".join("{:02X}".format(byte) for byte in decoded)
                    uri = uri.replace(f'pinSHA256=sha256/{match.group(1)}', f'pinSHA256={formatted}')
            processed_uris.append(uri)
        
        extra_uris = self._get_extra_configs()
        all_processed_uris = processed_uris + extra_uris

        if not all_processed_uris:
            return "No URI available"

        subscription_info = (
            f"//subscription-userinfo: upload={user_info.upload_bytes}; "
            f"download={user_info.download_bytes}; "
            f"total={user_info.max_download_bytes}; "
            f"expire={user_info.expiration_timestamp}\n"
        )
        print(f"Using profile title: {self.config.profile_title}")
        
        if self.config.show_username:
            title_str = f"{username}-{self.config.profile_title}"
        else:
            title_str = self.config.profile_title
            
        profile_lines = f"//profile-title: {title_str}\n//profile-update-interval: 1\n"
        
        if self.config.support_url:
            profile_lines += f"//profile-web-page-url: {self.config.support_url}\n"
            profile_lines += f"//support-url: {self.config.support_url}\n"
            
        return profile_lines + subscription_info + "\n".join(all_processed_uris)


class TemplateRenderer:
    def __init__(self, template_dir: str, config: AppConfig):
        self.env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        self.html_template = self.env.get_template('index.html')
        self.config = config

    def render(self, context: TemplateContext) -> str:
        return self.html_template.render(vars(context))


class HysteriaServer:
    def __init__(self):
        self.config = self._load_config()
        self.rate_limiter = RateLimiter(self.config.rate_limit, self.config.rate_limit_window)
        self.hysteria_cli = HysteriaCLI(self.config.hysteria_cli_path)
        self.singbox_generator = SingboxConfigGenerator(self.hysteria_cli, self.config.sni)
        self.singbox_generator.set_template_path(self.config.singbox_template_path)
        self.subscription_manager = SubscriptionManager(self.hysteria_cli, self.config)
        self.template_renderer = TemplateRenderer(self.config.template_dir, self.config)
        self.app = web.Application(middlewares=[
            self._invalid_endpoint_middleware,
            self._rate_limit_middleware,
            self._noindex_middleware
        ])

        safe_subpath = self.validate_subpath_for_routing(self.config.subpath)

        base_path = f'/{safe_subpath}'
        self.app.router.add_get(f'{base_path}/style.css', self.handle_style)
        self.app.router.add_get(f'{base_path}/script.js', self.handle_script)
        self.app.router.add_get(f'{base_path}/{{password_token}}', self.handle)
        self.app.router.add_get(f'{base_path}/robots.txt', self.robots_handler)
        self.app.router.add_route('*', f'{base_path}/{{tail:.*}}', self.handle_404_subpath)

    def _load_config(self) -> AppConfig:
        domain = os.getenv('HYSTERIA_DOMAIN', 'localhost')
        external_port = int(os.getenv('HYSTERIA_PORT', '443'))
        profile_title = os.getenv('PROFILE_TITLE', 'ANY')
        show_username = os.getenv('SHOW_USERNAME', 'true').lower() == 'true'
        support_url = os.getenv('SUPPORT_URL', '')
        aiohttp_listen_address = os.getenv('AIOHTTP_LISTEN_ADDRESS', '127.0.0.1')
        aiohttp_listen_port = int(os.getenv('AIOHTTP_LISTEN_PORT', '33261'))
        
        subpath = os.getenv('SUBPATH', '').strip().strip("/")
        if not subpath or not self.is_valid_subpath(subpath):
            raise ValueError(
                f"Invalid or empty SUBPATH: '{subpath}'. Subpath must be valid segments separated by slashes (e.g., 'path' or 'path/to/resource').")

        sni_file = '/etc/hysteria/.configs.env'
        singbox_template_path = '/etc/hysteria/core/scripts/normalsub/singbox.json'
        hysteria_cli_path = '/etc/hysteria/core/cli.py'
        nodes_json_path = '/etc/hysteria/nodes.json'
        extra_config_path = '/etc/hysteria/extra.json'
        rate_limit = 100
        rate_limit_window = 60
        template_dir = os.path.join(os.path.dirname(__file__), 'template')

        panel_config = self._load_panel_config(sni_file)
        sni = panel_config.get('SNI', 'bts.com')
        
        if not support_url:
            support_url = panel_config.get('SUPPORT_URL', '')

        return AppConfig(domain=domain, external_port=external_port,
                         aiohttp_listen_address=aiohttp_listen_address,
                         aiohttp_listen_port=aiohttp_listen_port,
                         sni_file=sni_file,
                         singbox_template_path=singbox_template_path,
                         hysteria_cli_path=hysteria_cli_path,
                         nodes_json_path=nodes_json_path,
                         extra_config_path=extra_config_path,
                         rate_limit=rate_limit, rate_limit_window=rate_limit_window,
                         sni=sni, template_dir=template_dir,
                         subpath=subpath, profile_title=profile_title, show_username=show_username,
                         support_url=support_url)

    def _load_panel_config(self, env_file: str) -> Dict[str, str]:
        config = {}
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except FileNotFoundError:
            print(f"Warning: Config file {env_file} not found.")
        except Exception as e:
            print(f"Warning: Error reading config file {env_file}: {e}")
        return config

    def is_valid_subpath(self, subpath: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9]+(?:/[a-zA-Z0-9]+)*$", subpath))

    def validate_subpath_for_routing(self, subpath: str) -> str:
        if not self.is_valid_subpath(subpath):
            raise ValueError(f"Invalid subpath: {subpath}")
        return subpath

    @middleware
    async def _rate_limit_middleware(self, request: web.Request, handler):
        client_ip_hdr = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP'))
        client_ip = client_ip_hdr.split(',')[0].strip() if client_ip_hdr else request.remote
        
        if client_ip and not self.rate_limiter.check_limit(client_ip):
            return web.Response(status=429, text="Rate limit exceeded.")
        return await handler(request)

    @middleware
    async def _invalid_endpoint_middleware(self, request: web.Request, handler):
        expected_prefix = f'/{self.config.subpath}/'
        if not request.path.startswith(expected_prefix):
            print(f"Warning: Request {request.path} reached aiohttp outside expected subpath {expected_prefix}. Closing connection.")
            if request.transport is not None:
                request.transport.close()
            raise web.HTTPForbidden()
        return await handler(request)

    @middleware
    async def _noindex_middleware(self, request: web.Request, handler):
        response = await handler(request)
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive, nosnippet'
        return response

    async def handle(self, request: web.Request) -> web.Response:
        try:
            password_token_raw = request.match_info.get('password_token', '')
            if not password_token_raw:
                 return web.Response(status=400, text="Error: Missing 'password_token' parameter.")
            
            password_token = Utils.sanitize_input(password_token_raw, r'^[a-zA-Z0-9]+$')

            username = self.hysteria_cli.get_username_by_password(password_token)
            if username is None:
                return web.Response(status=404, text="User not found for the provided token.")

            user_info = self.hysteria_cli.get_user_info(username)
            if user_info is None:
                return web.Response(status=404, text=f"User '{username}' details not found.")

            if user_info.blocked:
                return await self._handle_blocked_user(request, user_info)

            user_agent = request.headers.get('User-Agent', '').lower()
            if any(browser in user_agent for browser in ['chrome', 'firefox', 'safari', 'edge', 'opera']):
                return await self._handle_html(request, username, user_info)
            fragment = request.query.get('fragment', '')
            
            if 'hiddify' in user_agent:
                 return await self._handle_normalsub(request, username, user_info, password_token)

            if 'singbox' in user_agent or 'sing' in user_agent:
                return await self._handle_singbox(username, fragment, user_info, password_token)
            return await self._handle_normalsub(request, username, user_info, password_token)
        except ValueError as e:
            return web.Response(status=400, text=f"Error: {e}")
        except Exception as e:
            print(f"Internal Server Error: {e}")
            return web.Response(status=500, text="Error: Internal server error")

    async def _handle_blocked_user(self, request: web.Request, user_info: UserInfo) -> web.Response:
        fake_uri = "hysteria2://x@end.com:443?sni=support.me#⛔Account-Expired⚠️"
        user_agent = request.headers.get('User-Agent', '').lower()

        if any(browser in user_agent for browser in ['chrome', 'firefox', 'safari', 'edge', 'opera']):
            context = self._get_blocked_template_context(fake_uri, user_info)
            return web.Response(text=self.template_renderer.render(context), content_type='text/html')

        fragment = request.query.get('fragment', '')
        if 'singbox' in user_agent or 'sing' in user_agent:
            combined_config = self.singbox_generator.combine_configs([fake_uri], "blocked", fragment)
            return web.Response(text=json.dumps(combined_config, indent=4, sort_keys=True), content_type='application/json')
        
        return web.Response(text=fake_uri, content_type='text/plain')

    def _get_blocked_template_context(self, fake_uri: str, user_info: UserInfo) -> TemplateContext:
        return TemplateContext(
            username=user_info.username,
            usage=user_info.usage_human_readable,
            usage_raw="This account has been suspended.",
            days_remaining=0,
            expiration_date=user_info.expiration_date,
            status="Suspended",
            sublink_qrcode="",
            sub_link="#blocked",
            sub_link_encoded="",
            profile_title_encoded="",
            blocked=True,
            local_uris=[
                NodeURI(
                    label="Blocked",
                    uri=fake_uri,
                    qrcode=None
                )
            ],
            node_uris=[]
        )

    async def _handle_html(self, request: web.Request, username: str, user_info: UserInfo) -> web.Response:
        context = await self._get_template_context(username, user_info)
        return web.Response(text=self.template_renderer.render(context), content_type='text/html')

    async def _handle_singbox(self, username: str, fragment: str, user_info: UserInfo, password_token: str) -> web.Response:
        all_uris = self.hysteria_cli.get_all_uris(username)
        extra_uris = self.subscription_manager._get_extra_configs()
        all_uris.extend(extra_uris)

        if not all_uris:
            return web.Response(status=404, text=f"Error: No valid URIs found for user {username}.")
        combined_config = self.singbox_generator.combine_configs(all_uris, username, fragment)
        
        upload = user_info.upload_bytes
        download = user_info.download_bytes
        total = user_info.max_download_bytes
        expire = user_info.expiration_timestamp

        user_info_parts = [
            f"upload={upload}",
            f"download={download}"
        ]

        if total > 0:
            user_info_parts.append(f"total={total}")
        
        if expire > 0:
            user_info_parts.append(f"expire={expire}")

        port_str = f":{self.config.external_port}" if self.config.external_port not in [80, 443, 0] else ""
        web_page_url = f"https://{self.config.domain}{port_str}/{self.config.subpath}/{password_token}"

        headers = {
            "profile-title": f"base64:{base64.b64encode(self.config.profile_title.encode('utf-8')).decode('utf-8')}",
            "content-disposition": f'attachment; filename="{self.config.profile_title}.json"',
            "subscription-userinfo": "; ".join(user_info_parts),
            "profile-update-interval": "1",
            "profile-web-page-url": web_page_url
        }

        if self.config.support_url:
            headers['support-url'] = self.config.support_url

        return web.Response(
            text=json.dumps(combined_config, indent=4, sort_keys=True), 
            content_type='application/json',
            headers=headers
        )

    async def _handle_normalsub(self, request: web.Request, username: str, user_info: UserInfo, password_token: str) -> web.Response:
        user_agent = request.headers.get('User-Agent', '').lower()
        subscription = self.subscription_manager.get_normal_subscription(username, user_agent)
        if subscription == "User not found":
            return web.Response(status=404, text=f"User '{username}' not found.")
        
        port_str = f":{self.config.external_port}" if self.config.external_port not in [80, 443, 0] else ""
        web_page_url = f"https://{self.config.domain}{port_str}/{self.config.subpath}/{password_token}"
        
        headers = {
            'Subscription-Userinfo': f"upload={user_info.upload_bytes}; download={user_info.download_bytes}; total={user_info.max_download_bytes}; expire={user_info.expiration_timestamp}",
            'Profile-Title': self.config.profile_title,
            'Profile-Update-Interval': '1',
            'Profile-Web-Page-Url': web_page_url
        }
        
        if self.config.support_url:
            headers['Support-Url'] = self.config.support_url
        
        return web.Response(text=subscription, content_type='text/plain', headers=headers)

    async def _get_template_context(self, username: str, user_info: UserInfo) -> TemplateContext:
        labeled_uris = self.hysteria_cli.get_all_labeled_uris(username)
        port_str = f":{self.config.external_port}" if self.config.external_port not in [80, 443, 0] else ""
        base_url = f"https://{self.config.domain}{port_str}"

        if not Utils.is_valid_url(base_url):
            print(f"Warning: Constructed base URL '{base_url}' might be invalid. Check domain and port config.")
        
        sub_link = f"{base_url}/{self.config.subpath}/{user_info.password}"
        sub_link_encoded = quote(sub_link, safe='')
        sublink_qrcode = Utils.generate_qrcode_base64(sub_link)
        
        profile_title_encoded = quote(self.config.profile_title)
        
        singbox_qrcode = Utils.generate_qrcode_base64(f"sing-box://import-remote-profile?url={sub_link_encoded}#{profile_title_encoded}")
        hiddify_qrcode = Utils.generate_qrcode_base64(f"hiddify://import/{sub_link_encoded}#{profile_title_encoded}")
        streisand_qrcode = Utils.generate_qrcode_base64(f"streisand://import/sub?url={sub_link_encoded}#{profile_title_encoded}")
        nekobox_qrcode = Utils.generate_qrcode_base64(f"nekobox://import?url={sub_link_encoded}#{profile_title_encoded}")
        
        local_uris = []
        node_uris = []

        for item in labeled_uris:
            node_uri = NodeURI(
                label=item['label'], 
                uri=item['uri'], 
                qrcode=Utils.generate_qrcode_base64(item['uri'])
            )
            if item['label'].startswith('Node:'):
                node_uris.append(node_uri)
            else:
                local_uris.append(node_uri)

        current_timestamp = int(time.time())
        status = "Active"
        status_color = "emerald"

        if user_info.blocked:
            status = "Suspended"
        elif user_info.expiration_days > 0:
            if user_info.expiration_timestamp > 0 and user_info.expiration_timestamp < current_timestamp:
                status = "Expired"
        
        if user_info.max_download_bytes > 0:
            if user_info.total_usage >= user_info.max_download_bytes:
                status = "Data Limit Exceeded"

        days_remaining = 0
        if user_info.expiration_timestamp > 0:
            remaining_seconds = user_info.expiration_timestamp - current_timestamp
            if remaining_seconds > 0:
                days_remaining = int(remaining_seconds / 86400)

        return TemplateContext(
            username=username,
            usage=user_info.usage_human_readable,
            usage_raw=user_info.usage_detailed,
            expiration_date=user_info.expiration_date,
            days_remaining=days_remaining,
            status=status,
            sublink_qrcode=sublink_qrcode,
            sub_link=sub_link,
            sub_link_encoded=sub_link_encoded,
            profile_title_encoded=profile_title_encoded,
            blocked=user_info.blocked,
            local_uris=local_uris,
            node_uris=node_uris,
            singbox_qrcode=singbox_qrcode,
            hiddify_qrcode=hiddify_qrcode,
            streisand_qrcode=streisand_qrcode,
            nekobox_qrcode=nekobox_qrcode
        )

    async def robots_handler(self, request: web.Request) -> web.Response:
        return web.Response(text="User-agent: *\nDisallow: /", content_type="text/plain")

    async def handle_404_subpath(self, request: web.Request) -> web.Response:
        print(f"404 Not Found (within subpath, unhandled by specific routes): {request.path}")
        return web.Response(status=404, text="Not Found within Subpath")
    
    async def handle_style(self, request: web.Request) -> web.Response:
        return web.FileResponse(os.path.join(self.config.template_dir, 'style.css'))

    async def handle_script(self, request: web.Request) -> web.Response:
        return web.FileResponse(os.path.join(self.config.template_dir, 'script.js'))

    def run(self):
        print(f"Starting Hysteria Normalsub server on {self.config.aiohttp_listen_address}:{self.config.aiohttp_listen_port}")
        print(f"External access via Caddy should be at https://{self.config.domain}:{self.config.external_port}/{self.config.subpath}/<USER_PASSWORD>")
        web.run_app(
            self.app,
            host=self.config.aiohttp_listen_address,
            port=self.config.aiohttp_listen_port
        )

if __name__ == '__main__':
    server = HysteriaServer()
    server.run()