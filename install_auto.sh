#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[1;94m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

CHECK_MARK="[✓]"
CROSS_MARK="[✗]"
INFO_MARK="[i]"
WARNING_MARK="[!]"

HYSTERIA_SNI="google.com"
HYSTERIA_PORT=1935
PANEL_PORT=443
CLI_PATH="/etc/hysteria/core/cli.py"

log_info() { echo -e "${BLUE}${INFO_MARK} ${1}${NC}"; }
log_success() { echo -e "${GREEN}${CHECK_MARK} ${1}${NC}"; }
log_warning() { echo -e "${YELLOW}${WARNING_MARK} ${1}${NC}"; }
log_error() { echo -e "${RED}${CROSS_MARK} ${1}${NC}" >&2; }

handle_error() {
    log_error "Error occurred at line $1"
    exit 1
}
trap 'handle_error $LINENO' ERR

generate_password() {
    if command -v pwgen &> /dev/null; then
        pwgen -s 16 1
    else
        openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 16
    fi
}

generate_username() {
    echo "admin$(openssl rand -hex 3)"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root."
        exit 1
    fi
    log_info "Running with root privileges"
}

check_os_version() {
    local os_name os_version

    log_info "Checking OS compatibility..."

    if [ -f /etc/os-release ]; then
        os_name=$(grep '^ID=' /etc/os-release | cut -d= -f2)
        os_version=$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
    else
        log_error "Unsupported OS or unable to determine OS version."
        exit 1
    fi

    if ! command -v bc &> /dev/null; then
        log_info "Installing bc package..."
        apt update -qq && apt install -y -qq bc
    fi

    if [[ "$os_name" == "ubuntu" && $(echo "$os_version >= 22" | bc) -eq 1 ]] ||
       [[ "$os_name" == "debian" && $(echo "$os_version >= 12" | bc) -eq 1 ]]; then
        log_success "OS check passed: $os_name $os_version"
    else
        log_error "This script is only supported on Ubuntu 22+ or Debian 12+."
        exit 1
    fi

    log_info "Checking CPU for AVX support (required for MongoDB)..."
    if grep -q -m1 -o -E 'avx|avx2|avx512' /proc/cpuinfo; then
        log_success "CPU supports AVX instruction set."
    else
        log_warning "CPU does not support the AVX instruction set required for MongoDB."
        log_info "A 'nodb' version of the panel is available for systems without AVX support."
        echo ""
        read -p "$(echo -e "${YELLOW}Do you want to install the nodb version instead? (y/n): ${NC}")" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Switching to nodb installer..."
            exec bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/nodb/install.sh)
            exit 0
        else
            log_info "You can install it manually later:"
            echo -e "${YELLOW}bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/nodb/install.sh)${NC}"
            log_error "Installation aborted."
            exit 1
        fi
    fi
}

install_mongodb() {
    log_info "Installing MongoDB..."

    if command -v mongod &> /dev/null; then
        log_success "MongoDB is already installed"
        return 0
    fi

    curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor

    local codename
    codename=$(lsb_release -cs)
    local repo_line=""

    case "$codename" in
        "noble" | "jammy")
            repo_line="deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu $codename/mongodb-org/8.0 multiverse"
            ;;
        "bookworm" | "trixie")
            repo_line="deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main"
            ;;
        *)
            log_error "Unsupported OS codename for MongoDB installation: $codename"
            exit 1
            ;;
    esac

    echo "$repo_line" | tee /etc/apt/sources.list.d/mongodb-org-8.0.list > /dev/null

    apt update -qq
    apt install -y -qq mongodb-org

    systemctl enable mongod
    systemctl start mongod

    if systemctl is-active --quiet mongod; then
        log_success "MongoDB installed and started successfully"
    else
        log_error "MongoDB installation failed or service not running"
        exit 1
    fi
}

install_packages() {
    local REQUIRED_PACKAGES=("jq" "curl" "pwgen" "python3" "python3-pip" "python3-venv" "bc" "zip" "unzip" "lsof" "gnupg" "lsb-release" "certbot")
    local MISSING_PACKAGES=()

    log_info "Checking required packages..."

    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v "$package" &> /dev/null && ! dpkg -l | grep -q "^ii.*$package "; then
            MISSING_PACKAGES+=("$package")
        else
            log_success "Package $package is already installed"
        fi
    done

    if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
        log_info "Installing missing packages: ${MISSING_PACKAGES[*]}"
        apt update -qq || { log_error "Failed to update apt repositories"; exit 1; }
        apt upgrade -y -qq || { log_warning "Failed to upgrade packages, continuing..."; }

        for package in "${MISSING_PACKAGES[@]}"; do
            log_info "Installing $package..."
            if apt install -y -qq "$package"; then
                log_success "Installed $package"
            else
                log_error "Failed to install $package"
                exit 1
            fi
        done
    else
        log_success "All required packages are already installed."
    fi

    install_mongodb
}

download_and_extract_release() {
    log_info "Downloading and extracting ANY panel..."

    if [ -d "/etc/hysteria" ]; then
        log_warning "Directory /etc/hysteria already exists. Removing..."
        rm -rf /etc/hysteria
    fi

    local arch
    case $(uname -m) in
        x86_64) arch="amd64" ;;
        aarch64) arch="arm64" ;;
        *)
            log_error "Unsupported architecture: $(uname -m)"
            exit 1
            ;;
    esac
    log_info "Detected architecture: $arch"

    local zip_name="ANY-${arch}.zip"
    local download_url="https://github.com/0xd5f/ANY/releases/latest/download/${zip_name}"
    local temp_zip="/tmp/${zip_name}"

    log_info "Downloading from ${download_url}..."
    if curl -sL -o "$temp_zip" "$download_url"; then
        log_success "Download complete."
    else
        log_error "Failed to download the release asset."
        exit 1
    fi

    log_info "Extracting to /etc/hysteria..."
    mkdir -p /etc/hysteria
    if unzip -q "$temp_zip" -d /etc/hysteria; then
        log_success "Extracted successfully."
    else
        log_error "Failed to extract the archive."
        exit 1
    fi

    rm "$temp_zip"

    local auth_binary="/etc/hysteria/core/scripts/auth/user_auth"
    if [ -f "$auth_binary" ]; then
        chmod +x "$auth_binary"
        log_success "Set execute permission for auth binary."
    fi
}

setup_python_env() {
    log_info "Setting up Python virtual environment..."

    cd /etc/hysteria || { log_error "Failed to change to /etc/hysteria directory"; exit 1; }

    if python3 -m venv hysteria2_venv &> /dev/null; then
        log_success "Created Python virtual environment"
    else
        log_error "Failed to create Python virtual environment"
        exit 1
    fi

    source /etc/hysteria/hysteria2_venv/bin/activate || { log_error "Failed to activate virtual environment"; exit 1; }

    log_info "Installing Python requirements..."
    if pip install -r requirements.txt &> /dev/null; then
        log_success "Installed Python requirements"
    else
        log_error "Failed to install Python requirements"
        exit 1
    fi
}

add_alias() {
    if ! grep -q "alias any='source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/menu.sh'" ~/.bashrc; then
        echo "alias any='source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/menu.sh'" >> ~/.bashrc
        log_success "Added 'any' alias to .bashrc"
    fi
}

install_hysteria2() {
    log_info "Installing Hysteria2 (SNI: $HYSTERIA_SNI, Port: $HYSTERIA_PORT)..."

    source /etc/hysteria/hysteria2_venv/bin/activate
    cd /etc/hysteria

    python3 $CLI_PATH install-hysteria2 --port "$HYSTERIA_PORT" --sni "$HYSTERIA_SNI"

    cat <<EOF > /etc/hysteria/.configs.env
SNI=$HYSTERIA_SNI
EOF

    python3 $CLI_PATH ip-address

    if systemctl is-active --quiet hysteria-server.service; then
        log_success "Hysteria2 installed and running"
    else
        log_error "Hysteria2 failed to start"
        exit 1
    fi
}

install_webpanel() {
    local domain=$1
    local port=$PANEL_PORT
    local username=$(generate_username)
    local password=$(generate_password)

    log_info "Installing Web Panel (Domain: $domain, Port: $port)..."

    source /etc/hysteria/hysteria2_venv/bin/activate
    cd /etc/hysteria

    python3 $CLI_PATH webpanel -a start -d "$domain" -p "$port" -au "$username" -ap "$password"

    sleep 3

    if systemctl is-active --quiet hysteria-webpanel.service; then
        log_success "Web Panel installed and running"
    else
        log_error "Web Panel failed to start"
        exit 1
    fi

    source /etc/hysteria/core/scripts/webpanel/.env
    local panel_url="https://$domain:$port/$ROOT_PATH/"

    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}              ANY Panel — Installation Complete                ${NC}"
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Hysteria2${NC}"
    echo -e "  ├─ SNI:          ${BOLD}$HYSTERIA_SNI${NC}"
    echo -e "  └─ Port:         ${BOLD}$HYSTERIA_PORT${NC}"
    echo ""
    echo -e "  ${CYAN}Web Panel${NC}"
    echo -e "  ├─ URL:          ${BOLD}${panel_url}${NC}"
    echo -e "  ├─ Username:     ${BOLD}${username}${NC}"
    echo -e "  └─ Password:     ${BOLD}${password}${NC}"
    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${YELLOW}Save these credentials! They will not be shown again.${NC}"
    echo -e "  ${YELLOW}To open the menu later, type: ${BOLD}any${NC}"
    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
}

main() {
    echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}      ANY Panel — Auto Installer          ${NC}"
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════${NC}\n"

    check_root
    check_os_version

    while true; do
        read -e -p "$(echo -e "${CYAN}Enter the domain for the panel: ${NC}")" PANEL_DOMAIN
        if [ -z "$PANEL_DOMAIN" ]; then
            log_error "Domain cannot be empty."
        else
            break
        fi
    done

    echo ""
    log_info "Configuration:"
    echo -e "  Hysteria2 SNI:    $HYSTERIA_SNI"
    echo -e "  Hysteria2 Port:   $HYSTERIA_PORT"
    echo -e "  Panel Domain:     $PANEL_DOMAIN"
    echo -e "  Panel Port:       $PANEL_PORT"
    echo ""

    install_packages
    download_and_extract_release
    setup_python_env
    add_alias
    source ~/.bashrc &> /dev/null || true

    install_hysteria2
    install_webpanel "$PANEL_DOMAIN"
}

main
