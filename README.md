<div align="center">

# ANY Panel

### Hysteria 2 Management Made Simple

[![GitHub Release](https://img.shields.io/github/v/release/0xd5f/ANY?style=flat-square&color=blue)](https://github.com/0xd5f/ANY/releases)
[![License](https://img.shields.io/github/license/0xd5f/ANY?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Debian-orange?style=flat-square)](https://github.com/0xd5f/ANY)

<p align="center">
  A powerful, automated, and user-friendly management panel for Hysteria 2 proxy server.<br>
  Built with Python and Bash for maximum performance and ease of use.
</p>

</div>

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| 👥 **User Management** | Easily add, remove, and edit users with traffic limits and expiration dates. |
| 📊 **Traffic Monitoring** | Real-time usage tracking and automatic limit enforcement. |
| 🚀 **Protocol Support** | Full Hysteria 2 support with VLESS/Trojan compatibility. |
| 💻 **Web Interface** | Modern, responsive web panel for managing your server from anywhere. |
| 🤖 **Telegram Bot** | Control your server directly via a Telegram Bot. |
| ⚡ **One-Click Install** | Automated script to get you up and running in seconds. |

## 📋 Requirements

*   **OS:** Ubuntu 22.04+ or Debian 12+
*   **CPU:** x86_64 with AVX support (Required for MongoDB 5.0+)
*   **Access:** Root privileges
*   **Ports:** 443 (default) or any custom port

## 🚀 Installation

### Quick Start (Recommended)

Run the following command on a fresh server to install automatically:

```bash
bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/main/install.sh)
```

### Manual Installation

If you prefer to install manually or from a local copy:

1.  Upload the files to your server.
2.  Run the installer:
    ```bash
    chmod +x install.sh
    sudo ./install.sh
    ```

## 🛠 Usage

Once installed, you can access the management menu at any time using the alias:

```bash
pany
```

Or by running the script directly:
```bash
./menu.sh
```

### 🖥️ Web Panel
If you installed the Web Panel, access it via your browser:
*   **URL:** `http://YOUR_IP:PORT/YOUR_SECRET_PATH`
*   **Default Port:** 8080 (or user defined)

## ⚠️ Production Setup

For a secure production environment, please follow these steps:

1.  Copy `config.example.json` to `config.json` and update all secrets.
2.  Copy `.env.example` to `.env` and set `DEBUG=false`.
3.  Enable MongoDB authentication.
4.  Refer to [PRODUCTION.md](PRODUCTION.md) for the complete guide.

## 📂 Project Structure

*   `core/` - Core Python modules and API logic
*   `install.sh` - automated installation script
*   `menu.sh` - Interactive CLI management menu
*   `requirements.txt` - Python dependencies

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 💖 Sponsorship & Support

If you find this project useful, please consider supporting its development!

### 🖥️ Recommended Hosting
[**4VPS.SU**](https://4vps.su/r/hcndRIOoxZGh) - Reliable and affordable VPS hosting.

### 🪙 Crypto Donations

Your support helps keep the project alive and updated.

| Cryptocurrency | Address |
| :--- | :--- |
| **BTC** | `bc1qhtfxycw57z6c2xfsaa5hfp8gws4jjrnsyq57n4` |
| **TRX (Tron)** | `TEmnHg48yLneutMqk9BDP79uMqQQ2LNFxx` |
| **USDT (TRC20)** | `TEmnHg48yLneutMqk9BDP79uMqQQ2LNFxx` |
| **TON** | `UQCIMGaysD8Ayl1lx_LAdld9NVnTcMxIF5lA-dlMmUqM1s96` |

### 📞 Contact

| Platform | Link |
| :--- | :--- |
| **Telegram** | [Oxd5f](https://t.me/Oxd5f) |
| **Email** | `oxd5f@proton.me` |