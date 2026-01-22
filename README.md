# Any Panel (Hysteria 2 Management Panel)

A powerful and easy-to-use management panel for Hysteria 2 proxy server, built with Python and Bash.

## ⚠️ Production Setup

Before deploying to production:
1. Copy `config.example.json` to `config.json` and update all secrets
2. Copy `.env.example` to `.env` and set `DEBUG=false`
3. Enable MongoDB authentication
4. See [PRODUCTION.md](PRODUCTION.md) for complete guide

## Features

- **User Management**: Add, remove, edit users with traffic limits and expiration dates.
- **Traffic Monitoring**: Track usage and reset limits.
- **Protocol Support**: Hysteria 2 with VLESS/Trojan compatibility.
- **Web Panel**: (Optional) Admin interface for management.
- **Telegram Bot**: (Optional) Control your server via Telegram.
- **Installation**: One-click installation script.

## Requirements

- **OS**: Ubuntu 22.04+ or Debian 12+
- **CPU**: Support for AVX instructions (Required for MongoDB 5.0+)
- **Root Access**: Required for installation and management.
- **Ports**: 
  - Hysteria server port (User defined, default 443 or custom)
  - SSH port (22)

## Installation

### Automatic Installation (Recommended)

To install the panel on a fresh server, clone the repository and run the installation script:

```bash
# Clone the repository
git clone https://github.com/0xd5f/any-panel.git /root/any-panel

# Enter the directory
cd /root/any-panel

# Run the installer
chmod +x install.sh
sudo ./install.sh
```

### Manual / Local Installation

If you have downloaded the files manually:

1. Upload the files to your server.
2. Ensure `core/`, `menu.sh`, and `requirements.txt` are in the same folder as `install.sh`.
3. Run:
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```

## Usage

After installation, you can manage the panel using the CLI menu:

```bash
hysteria-panel
# OR directly via script
./menu.sh
```

### Menu Options
1. **Install Hysteria 2**: Set up the core server.
2. **User Management**: Add, delete, or modify users.
3. **Traffic**: View traffic usage.
4. **Service Status**: Check if services are running.
5. **Update**: Update the panel core.

## Project Structure

- `core/`: Core Python modules for API and CLI interactions
- `core/scripts/`: Scripts for Hysteria, Bot, Database management
- `install.sh`: Main installation script
- `menu.sh`: Interactive management menu
- `requirements.txt`: Python dependencies

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add some amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

## License

See [LICENSE](LICENSE) file for details.
