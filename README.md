<img width="1600" height="920" alt="ANY Panel — Hysteria 2 Management" src="https://github.com/user-attachments/assets/f5a158ef-8953-4fc6-945c-605f23786892" />

<div align="center">

# ANY Panel

### Hysteria 2 Management Made Simple

[![GitHub Release](https://img.shields.io/github/v/release/0xd5f/ANY?style=flat-square&color=blue)](https://github.com/0xd5f/ANY/releases)
[![License](https://img.shields.io/github/license/0xd5f/ANY?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Debian-orange?style=flat-square)](https://github.com/0xd5f/ANY)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Hysteria](https://img.shields.io/badge/Hysteria-2-9B59B6?style=flat-square)](https://hysteria.network)
[![Telegram](https://img.shields.io/badge/Telegram-Channel-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/any_panel)

<p align="center">
  A powerful, automated, and user-friendly management panel for Hysteria 2 proxy server.<br>
  Built with Python and Bash for maximum performance and ease of use.<br><br>
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-web-panel">Web Panel</a> •
  <a href="#-api">API</a> •
  <a href="#-telegram-bot">Telegram Bot</a> •
  <a href="#-sponsorship--support">Support</a>
</p>

</div>

---

## 📑 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Quick Start](#-quick-start)
- [Installation Options](#-installation-options)
- [Usage — CLI Menu](#-usage--cli-menu)
- [Web Panel](#-web-panel)
- [API](#-api)
- [Telegram Bot](#-telegram-bot)
- [Anti-Censorship](#-anti-censorship)
- [Port Hopping](#-port-hopping)
- [WARP Integration](#-warp-integration)
- [Normal Subscription](#-normal-subscription)
- [Architecture](#-architecture)
- [Changelog](#-changelog)
- [License](#-license)
- [Sponsorship & Support](#-sponsorship--support)

---

## ✨ Features

<table>
  <tr>
    <td width="50%">

### Core
| | |
|:--|:--|
| 👥 **User Management** | Add, edit, remove users with traffic limits & expiration |
| 📊 **Traffic Monitoring** | Real-time usage tracking & automatic enforcement |
| 🔄 **Subscription Renewal** | One-click renew via API or panel |
| 🚫 **Block / Unblock** | Toggle user access with auto-renew on unblock |
| 📦 **Bulk Operations** | Mass import / export users via CSV |
| 💾 **Backup & Restore** | Full database backup & one-command restore |

  </td>
  <td width="50%">

### Infrastructure
| | |
|:--|:--|
| 🌐 **Web Panel** | Modern responsive UI, accessible from anywhere |
| 🤖 **Telegram Bot** | Full server control from Telegram (admin + reseller) |
| 🔌 **REST API** | Complete API with Swagger-style documentation |
| 🛡️ **Masquerade** | String & Proxy modes to bypass DPI fingerprinting |
| 🔀 **Port Hopping** | Automatic port rotation with configurable interval |
| 🌍 **WARP** | Cloudflare WARP integration for geo-routing |

  </td>
  </tr>
</table>

---

## 📋 Requirements

| Requirement | Details |
|:---|:---|
| **OS** | Ubuntu 22.04+ / Debian 12+ |
| **CPU** | x86_64 with AVX support (for MongoDB); see [No-AVX](#-no-avx-support-nodb-version) for alternatives |
| **RAM** | 512 MB minimum, 1 GB recommended |
| **Disk** | 2 GB free space minimum |
| **Access** | Root privileges (`sudo`) |
| **Network** | Open ports: Hysteria (default `443`) + Web Panel (custom) |
| **Domain** | Required for Web Panel HTTPS & masquerade proxy |

---

## 🚀 Quick Start

Run one command on a fresh server:

```bash
bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/main/install.sh)
```

The interactive installer will guide you through selecting a port, SNI, and optional components (Web Panel, Telegram Bot, WARP).

---

## 📦 Installation Options

### 1. Interactive Installation (Recommended)

Full control over every setting — port, SNI, panel, bot, WARP:

```bash
bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/main/install.sh)
```

### 2. Fully Automated Installation

Zero-interaction setup — asks only for your domain. Auto-generates admin credentials and outputs the panel URL:

```bash
bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/main/install_auto.sh)
```

<details>
<summary><b>What does the auto installer configure?</b></summary>

| Parameter | Default Value |
|:---|:---|
| Hysteria 2 Port | `1935` |
| SNI | `google.com` |
| Web Panel Port | `443` |
| Self-signed Certificate | No (uses domain) |
| Username | `admin` + random 6-char hex |
| Password | Random 16-char secure string |

After installation, the script outputs:
```
╔══════════════════════════════════════╗
║        ANY Panel Credentials         ║
╠══════════════════════════════════════╣
║  URL:      https://domain/path       ║
║  Login:    admin8f3a2c               ║
║  Password: xK9mR2pL...              ║
╚══════════════════════════════════════╝
```
</details>

### 3. Manual Installation

```bash
git clone https://github.com/0xd5f/ANY.git
cd ANY
chmod +x install.sh
sudo ./install.sh
```

---

## ⚠️ No-AVX Support (nodb version)

MongoDB 5.0+ requires the **AVX** CPU instruction set. If your server's CPU doesn't support AVX (common on older or budget VPS), the installer will detect this and offer to switch to the **nodb** version automatically.

You can also install it directly:

```bash
bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/nodb/install.sh)
```

<details>
<summary><b>How to check if your CPU has AVX</b></summary>

```bash
grep -o -m1 'avx' /proc/cpuinfo && echo "AVX supported" || echo "No AVX — use nodb version"
```
</details>

> **Note:** The `nodb` version uses file-based storage instead of MongoDB. All panel features remain available.

---

## 🛠 Usage — CLI Menu

After installation, access the management menu:

```bash
any
```

<details>
<summary><b>CLI Menu Options</b></summary>

```
╔══════════════════════════════════════════════╗
║              ANY Panel - Main Menu           ║
╠══════════════════════════════════════════════╣
║  1) User Management                         ║
║  2) Server Management                       ║
║  3) Hysteria 2 Settings                     ║
║  4) Web Panel                                ║
║  5) Telegram Bot                             ║
║  6) WARP                                     ║
║  7) Normal Subscription                      ║
║  8) Update                                   ║
║  9) Uninstall                                ║
║  0) Exit                                     ║
╚══════════════════════════════════════════════╝
```
</details>

---

## 🖥️ Web Panel

A fully-featured web interface for managing Hysteria 2 — no terminal required.

**Access:** `https://YOUR_DOMAIN:PORT/SECRET_PATH`

### Panel Sections

| Section | Description |
|:---|:---|
| **Dashboard** | Server status, active users, traffic overview |
| **Users** | Add / edit / delete / block / renew users |
| **Hysteria Settings** | Port, SNI, masquerade mode, port hopping, GeoIP |
| **Config** | Server configuration, WARP, subscription links |
| **API Docs** | Built-in interactive API documentation |
| **Settings** | Admin credentials, panel port, secret path |

### Key UI Features

- **Real-time traffic stats** per user with progress bars
- **One-click URI copy** and QR code generation
- **Block/Unblock toggle** with automatic creation date renewal
- **Masquerade mode selector** — choose between String and Proxy
- **Port Hopping** with customizable hop interval (5–300 sec)
- **Dark mode** responsive design

---

## 🔌 API

The panel exposes a REST API at `/api/v1/` for programmatic access. All endpoints require authentication via the admin session.

### Key Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/v1/users` | List all users |
| `POST` | `/api/v1/users` | Create a new user |
| `GET` | `/api/v1/user/{username}` | Get user details |
| `PUT` | `/api/v1/user/{username}` | Edit user |
| `DELETE` | `/api/v1/user/{username}` | Delete user |
| `POST` | `/api/v1/user/{username}/renew` | Renew subscription |
| `POST` | `/api/v1/user/{username}/reset` | Reset traffic |
| `GET` | `/api/v1/server/info` | Server information |
| `GET` | `/api/v1/hysteria/check-masquerade` | Masquerade status |
| `POST` | `/api/v1/hysteria/masquerade/enable` | Enable masquerade |
| `POST` | `/api/v1/hysteria/port-hopping/enable` | Enable port hopping |

<details>
<summary><b>Example: Renew User Subscription</b></summary>

```bash
curl -X POST "https://your-panel/api/v1/user/john/renew" \
  -H "Content-Type: application/json" \
  -d '{
    "expiration_days": 30,
    "traffic_limit": 50,
    "reset_traffic": true
  }'
```

Response:
```json
{
  "status": "success",
  "message": "User john renewed successfully"
}
```
</details>

Full interactive API documentation is available at **Settings → API Docs** in the Web Panel.

---

## 🤖 Telegram Bot

Control your server directly from Telegram — available in admin and reseller modes.

### Bot Commands

| Command | Description |
|:---|:---|
| `/start` | Start the bot and show the main menu |
| `/adduser` | Create a new user |
| `/deleteuser` | Remove a user |
| `/edituser` | Edit user settings |
| `/search` | Search for a user |
| `/serverinfo` | Show server status & stats |
| `/backup` | Create and download a backup |
| `/settings` | Bot and server settings |

### Reseller Mode

A separate bot instance (`hysteria-reseller-bot.service`) allows resellers to manage their own users with limited permissions — no access to server settings or other users.

---

## 🛡️ Anti-Censorship

### Masquerade

Masquerade hides Hysteria 2 traffic from DPI (Deep Packet Inspection) by mimicking a normal HTTPS website.

| Mode | Description |
|:---|:---|
| **String** | Returns a static HTML page (default "502 Bad Gateway") for probing requests |
| **Proxy** | Reverse-proxies a real website (e.g. `https://google.com`) — makes the server look like a legitimate site to censors |

> **Proxy mode** is recommended for high-censorship environments. The target site is fully mirrored, including headers and content, making detection significantly harder.

**Configure via:**
- Web Panel → Hysteria Settings → Masquerade
- API: `POST /api/v1/hysteria/masquerade/enable?mode=proxy&proxy_url=https://google.com`
- CLI: `any` → Hysteria 2 Settings → Masquerade

---

## 🔀 Port Hopping

Port Hopping distributes Hysteria 2 traffic across a range of ports using `iptables` NAT rules. This defeats port-based traffic analysis and blocking.

| Parameter | Description |
|:---|:---|
| **Port Range** | e.g. `20000-40000` — incoming ports that redirect to the Hysteria port |
| **Hop Interval** | `5–300` seconds — how often clients switch to a new port |

Clients automatically receive the `mport` parameter and hop interval in their subscription URIs.

**Configure via:** Web Panel → Hysteria Settings → Port Hopping

---

## 🌍 WARP Integration

Cloudflare WARP can be used as an outbound proxy to:
- Bypass IP-based geo-restrictions
- Route traffic through Cloudflare's network
- Obtain a clean IP address for accessing restricted services

**Configure via:** CLI menu → WARP → Install / Configure / Status

---

## 📡 Normal Subscription

A web-based subscription endpoint that generates client configs on the fly — compatible with Sing-Box, Hiddify, and other Hysteria 2 clients.

| Feature | Details |
|:---|:---|
| **Format** | Sing-Box JSON configuration |
| **Port Hopping** | Automatically included when enabled |
| **Hop Interval** | Passed to client config |
| **Access** | `https://YOUR_DOMAIN/sub/SECRET/USERNAME` |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                     ANY Panel                        │
├──────────────┬──────────────┬────────────────────────┤
│  Web Panel   │ Telegram Bot │      CLI Menu          │
│  (FastAPI)   │  (aiogram)   │      (Bash)            │
├──────────────┴──────────────┴────────────────────────┤
│                    CLI API (Python)                   │
│              core/cli_api.py — unified bridge         │
├──────────────────────────────────────────────────────┤
│               Hysteria 2 Scripts Layer               │
│  add_user │ edit_user │ backup │ masquerade │ ...    │
├──────────────────────────────────────────────────────┤
│                  MongoDB (User DB)                   │
├──────────────────────────────────────────────────────┤
│              Hysteria 2 Server (Go binary)           │
│           config.json • auth server • ACL            │
└──────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|:---|:---|
| Proxy Server | Hysteria 2 (QUIC-based, Go) |
| Database | MongoDB 5.0+ |
| Web Panel | FastAPI + Jinja2 + vanilla JS |
| Telegram Bot | Python (aiogram) |
| CLI | Bash + Python |
| Authentication | Go auth server (`user_auth.go`) |
| Package Management | pip + requirements.txt |

### Project Structure

```
ANY/
├── install.sh             # Interactive installer
├── install_auto.sh        # Fully automated installer
├── menu.sh                # CLI management menu
├── deploy.py              # Deployment tool (SSH/SCP)
├── config.json            # Panel configuration
├── requirements.txt       # Python dependencies
│
└── core/
    ├── cli.py             # CLI command router
    ├── cli_api.py         # Unified API bridge
    ├── traffic.py         # Traffic tracking
    │
    └── scripts/
        ├── hysteria2/     # Hysteria 2 management scripts
        ├── webpanel/      # Web panel (FastAPI app)
        ├── telegrambot/   # Telegram bot
        ├── normalsub/     # Subscription endpoint
        ├── warp/          # WARP integration
        ├── nodes/         # Multi-node support
        ├── tcp-brutal/    # TCP Brutal installer
        └── db/            # Database management
```

---

## 📝 Changelog

See [changelog.md](changelog.md) for the full release history.

**Latest — v1.4.7:**
- Masquerade Proxy mode
- Renew API endpoint
- Port Hopping hop interval
- Auto installer
- Block User toggle fix

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 💖 Sponsorship & Support

If you find this project useful, please consider supporting its development!

### 🖥️ Recommended Hosting

[**4VPS.SU**](https://4vps.su/r/hcndRIOoxZGh) — Reliable and affordable VPS hosting, perfect for running ANY Panel.

### 🪙 Crypto Donations

Your support helps keep the project alive and updated.

| Cryptocurrency | Address |
|:---|:---|
| **BTC** | `bc1qhtfxycw57z6c2xfsaa5hfp8gws4jjrnsyq57n4` |
| **TRX (Tron)** | `TEmnHg48yLneutMqk9BDP79uMqQQ2LNFxx` |
| **USDT (TRC20)** | `TEmnHg48yLneutMqk9BDP79uMqQQ2LNFxx` |
| **TON** | `UQCIMGaysD8Ayl1lx_LAdld9NVnTcMxIF5lA-dlMmUqM1s96` |

### 📞 Contact & Community

| Platform | Link |
|:---|:---|
| **Telegram Channel** | [@any_panel](https://t.me/any_panel) |
| **Email** | `oxd5f@proton.me` |

### 🔗 Forks & Derivatives

| Project | Link |
|:---|:---|
| **Blitz** | [ReturnFI/Blitz](https://github.com/ReturnFI/Blitz) |
