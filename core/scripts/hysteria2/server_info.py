import sys
import json
import asyncio
import aiofiles
import time
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import init_paths
from db.database import db


def convert_bytes(bytes_val: int) -> str:
    if bytes_val >= (1 << 40):
        return f"{bytes_val / (1 << 40):.2f} TB"
    elif bytes_val >= (1 << 30):
        return f"{bytes_val / (1 << 30):.2f} GB"
    elif bytes_val >= (1 << 20):
        return f"{bytes_val / (1 << 20):.2f} MB"
    elif bytes_val >= (1 << 10):
        return f"{bytes_val / (1 << 10):.2f} KB"
    return f"{bytes_val} B"


def convert_speed(bytes_per_second: int) -> str:
    if bytes_per_second >= (1 << 40):
        return f"{bytes_per_second / (1 << 40):.2f} TB/s"
    elif bytes_per_second >= (1 << 30):
        return f"{bytes_per_second / (1 << 30):.2f} GB/s"
    elif bytes_per_second >= (1 << 20):
        return f"{bytes_per_second / (1 << 20):.2f} MB/s"
    elif bytes_per_second >= (1 << 10):
        return f"{bytes_per_second / (1 << 10):.2f} KB/s"
    return f"{int(bytes_per_second)} B/s"


async def read_file_async(filepath: str) -> str:
    try:
        async with aiofiles.open(filepath, 'r') as f:
            return await f.read()
    except FileNotFoundError:
        return ""


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m"


async def get_uptime_and_boottime() -> tuple[str, str]:
    try:
        content = await read_file_async("/proc/uptime")
        uptime_seconds = float(content.split()[0])
        boot_time_epoch = time.time() - uptime_seconds
        boot_time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(boot_time_epoch))
        uptime_str = format_uptime(uptime_seconds)
        return uptime_str, boot_time_str
    except (FileNotFoundError, IndexError, ValueError):
        return "N/A", "N/A"


def parse_cpu_stats(content: str) -> tuple[int, int]:
    if not content:
        return 0, 0
    line = content.split('\n')[0]
    fields = list(map(int, line.strip().split()[1:]))
    idle, total = fields[3], sum(fields)
    return idle, total


async def get_cpu_usage(interval: float = 0.1) -> float:
    content1 = await read_file_async("/proc/stat")
    idle1, total1 = parse_cpu_stats(content1)
    
    await asyncio.sleep(interval)
    
    content2 = await read_file_async("/proc/stat")
    idle2, total2 = parse_cpu_stats(content2)

    idle_delta = idle2 - idle1
    total_delta = total2 - total1
    cpu_usage = 100.0 * (1 - idle_delta / total_delta) if total_delta else 0.0
    return round(cpu_usage, 1)


def parse_meminfo(content: str) -> tuple[int, int]:
    if not content:
        return 0, 0
    
    mem_info = {}
    for line in content.split('\n'):
        if ':' in line:
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(':')
                if parts[1].isdigit():
                    mem_info[key] = int(parts[1])

    mem_total_kb = mem_info.get("MemTotal", 0)
    mem_free_kb = mem_info.get("MemFree", 0)
    buffers_kb = mem_info.get("Buffers", 0)
    cached_kb = mem_info.get("Cached", 0)
    sreclaimable_kb = mem_info.get("SReclaimable", 0)

    used_kb = mem_total_kb - mem_free_kb - buffers_kb - cached_kb - sreclaimable_kb

    used_kb = max(0, used_kb)
    return mem_total_kb // 1024, used_kb // 1024


async def get_memory_usage() -> tuple[int, int]:
    content = await read_file_async("/proc/meminfo")
    return parse_meminfo(content)


def parse_network_stats(content: str) -> tuple[int, int]:
    if not content:
        return 0, 0
    
    rx_bytes, tx_bytes = 0, 0
    lines = content.split('\n')
    
    for line in lines[2:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 10:
            continue
        iface = parts[0].strip().replace(':', '')
        if iface == 'lo':
            continue
        try:
            rx_bytes += int(parts[1])
            tx_bytes += int(parts[9])
        except (IndexError, ValueError):
            continue
    
    return rx_bytes, tx_bytes


async def get_network_stats() -> tuple[int, int]:
    content = await read_file_async('/proc/net/dev')
    return parse_network_stats(content)


async def get_network_speed(interval: float = 0.5) -> tuple[int, int]:
    rx1, tx1 = await get_network_stats()
    await asyncio.sleep(interval)
    rx2, tx2 = await get_network_stats()
    
    rx_speed = (rx2 - rx1) / interval
    tx_speed = (tx2 - tx1) / interval
    return int(rx_speed), int(tx_speed)


def parse_connection_counts(tcp_content: str, udp_content: str) -> tuple[int, int]:
    tcp_count = len(tcp_content.split('\n')) - 2 if tcp_content else 0
    udp_count = len(udp_content.split('\n')) - 2 if udp_content else 0
    return max(0, tcp_count), max(0, udp_count)


async def get_connection_counts() -> tuple[int, int]:
    tcp_task = read_file_async('/proc/net/tcp')
    udp_task = read_file_async('/proc/net/udp')
    tcp_content, udp_content = await asyncio.gather(tcp_task, udp_task)
    return parse_connection_counts(tcp_content, udp_content)


def get_online_user_count_sync() -> int:
    if db is None:
        print("Error: Database connection failed.", file=sys.stderr)
        return 0
    try:
        users = db.get_all_users()
        total_online = sum(int(user.get("online_count", 0) or 0) for user in users)
        return total_online
    except Exception as e:
        print(f"Error retrieving online user count from database: {e}", file=sys.stderr)
        return 0


async def get_online_user_count() -> int:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, get_online_user_count_sync)


def get_user_traffic_sync() -> tuple[int, int]:
    if db is None:
        print("Error: Database connection failed.", file=sys.stderr)
        return 0, 0
    try:
        users = db.get_all_users()
        total_upload = sum(int(user.get("upload_bytes", 0) or 0) for user in users)
        total_download = sum(int(user.get("download_bytes", 0) or 0) for user in users)
        return total_upload, total_download
    except Exception as e:
        print(f"Error retrieving user traffic from database: {e}", file=sys.stderr)
        return 0, 0


async def get_user_traffic() -> tuple[int, int]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, get_user_traffic_sync)


def get_interface_addresses():
    ipv4_address = ""
    ipv6_address = ""

    try:
        interfaces_output = subprocess.check_output(["ip", "-o", "link", "show"]).decode()
        interface_lines = interfaces_output.strip().splitlines()
        
        interfaces = []
        for line in interface_lines:
            parts = line.split(': ')
            if len(parts) > 1:
                iface_name = parts[1].split('@')[0]
                if not re.match(r"^(lo|wgcf|warp)", iface_name):
                    interfaces.append(iface_name)

        for iface in interfaces:
            try:
                if not ipv4_address:
                    ipv4_output = subprocess.check_output(["ip", "-o", "-4", "addr", "show", iface]).decode()
                    for line in ipv4_output.strip().splitlines():
                        addr = line.split()[3].split("/")[0]
                        if not re.match(r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1]))", addr):
                            ipv4_address = addr
                            break
                if not ipv6_address:
                    ipv6_output = subprocess.check_output(["ip", "-o", "-6", "addr", "show", iface]).decode()
                    for line in ipv6_output.strip().splitlines():
                        addr = line.split()[3].split("/")[0]
                        if not re.match(r"^(::1|fe80:)", addr):
                            ipv6_address = addr
                            break
            except subprocess.CalledProcessError:
                continue
            if ipv4_address and ipv6_address:
                break
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return ipv4_address, ipv6_address


async def get_interface_addresses_async():
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, get_interface_addresses)


async def main():
    tasks = [
        get_uptime_and_boottime(),
        get_memory_usage(),
        get_connection_counts(),
        get_online_user_count(),
        get_user_traffic(),
        get_cpu_usage(0.1),
        get_network_speed(0.3),
        get_network_stats(),
        get_interface_addresses_async()
    ]
    
    results = await asyncio.gather(*tasks)
    
    uptime_str, boot_time_str = results[0]
    mem_total, mem_used = results[1]
    tcp_connections, udp_connections = results[2]
    online_users = results[3]
    user_upload, user_download = results[4]
    cpu_usage = results[5]
    download_speed, upload_speed = results[6]
    reboot_rx, reboot_tx = results[7]
    ipv4_address, ipv6_address = results[8]

    print(f"🕒 Uptime: {uptime_str} (since {boot_time_str})")
    print(f"🖥️ Server IPv4: {ipv4_address if ipv4_address else 'Not Found'}")
    print(f"🖥️ Server IPv6: {ipv6_address if ipv6_address else 'Not Found'}")
    print(f"📈 CPU Usage: {cpu_usage}%")
    print(f"💻 Used RAM: {mem_used}MB / {mem_total}MB")
    print(f"👥 Online Users: {online_users}")
    print()
    print(f"🔼 Upload Speed: {convert_speed(upload_speed)}")
    print(f"🔽 Download Speed: {convert_speed(download_speed)}")
    print(f"📡 TCP Connections: {tcp_connections}")
    print(f"📡 UDP Connections: {udp_connections}")
    print()
    print("📊 Traffic Since Last Reboot:")
    print(f"   🔼 Total Uploaded: {convert_bytes(reboot_tx)}")
    print(f"   🔽 Total Downloaded: {convert_bytes(reboot_rx)}")
    print(f"   📈 Combined Traffic: {convert_bytes(reboot_tx + reboot_rx)}")
    print()
    print("📊 User Traffic (All Time):")
    print(f"   🔼 Uploaded Traffic: {convert_bytes(user_upload)}")
    print(f"   🔽 Downloaded Traffic: {convert_bytes(user_download)}")
    print(f"   📈 Total Traffic: {convert_bytes(user_upload + user_download)}")


if __name__ == "__main__":
    asyncio.run(main())