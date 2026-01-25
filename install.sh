#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[1;94m'
NC='\033[0m'
BOLD='\033[1m'

CHECK_MARK="[✓]"
CROSS_MARK="[✗]"
INFO_MARK="[i]"
WARNING_MARK="[!]"

log_info() {
    echo -e "${BLUE}${INFO_MARK} ${1}${NC}"
}

log_success() {
    echo -e "${GREEN}${CHECK_MARK} ${1}${NC}"
}

log_warning() {
    echo -e "${YELLOW}${WARNING_MARK} ${1}${NC}"
}

log_error() {
    echo -e "${RED}${CROSS_MARK} ${1}${NC}" >&2
}

handle_error() {
    log_error "Error occurred at line $1"
    exit 1
}

trap 'handle_error $LINENO' ERR

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
        if [ $? -ne 0 ]; then
            log_error "Failed to install bc package."
            exit 1
        fi
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
        log_error "CPU does not support the required AVX instruction set for MongoDB."
        log_info "For systems without AVX support, you can use the 'nodb' version of the panel."
        log_info "To install it, please run the following command:"
        echo -e "${YELLOW}bash <(curl -sL https://raw.githubusercontent.com/0xd5f/ANY/main/install.sh)${NC}"
        log_error "Installation aborted."
        exit 1
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
    local REQUIRED_PACKAGES=("jq" "curl" "pwgen" "python3" "python3-pip" "python3-venv" "bc" "zip" "unzip" "lsof" "gnupg" "lsb-release")
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
    log_info "Downloading and extracting any panel..."

    if [ -d "/etc/hysteria" ]; then
        log_warning "Directory /etc/hysteria already exists."
        read -p "Do you want to remove it and install again? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf /etc/hysteria
        else
            log_info "Skipping download. Using existing directory."
            return 0
        fi
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

    local zip_name="any-${arch}.zip"
    local download_url="https://github.com/0xd5f/ANY/releases/latest/download/${zip_name}"
    local temp_zip="/tmp/${zip_name}"

    log_info "Downloading from ${download_url}..."
    if curl -sL -o "$temp_zip" "$download_url"; then
        log_success "Download complete."
    else
        log_error "Failed to download the release asset. Please check the URL and your connection."
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
    log_info "Cleaned up temporary file."
    
    local auth_binary="/etc/hysteria/core/scripts/auth/user_auth"
    if [ -f "$auth_binary" ]; then
        chmod +x "$auth_binary"
        log_success "Set execute permission for auth binary."
    else
        log_warning "Auth binary not found at $auth_binary. The installation might be incomplete."
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

configure_hysteria() {
    log_info "Configuring Hysteria2..."
    
    if systemctl is-active --quiet hysteria-server.service; then
        log_info "Hysteria server is already running. Skipping configuration."
        return 0
    fi

    local port="1935"
    local sni="github.com"

    log_info "Auto-installing Hysteria2 with Port: $port and SNI: $sni"

    if python3 core/cli.py install-hysteria2 --port "$port" --sni "$sni"; then
        log_success "Hysteria2 configured successfully."
        echo "SNI=$sni" > /etc/hysteria/.configs.env
    else
        log_error "Failed to configure Hysteria2."
        exit 1
    fi
}

configure_webpanel() {
    log_info "Configuring Web Panel..."

    if systemctl is-active --quiet hysteria-webpanel.service; then
         log_info "Web Panel is already running."
         return 0
    fi

    read -p "Do you want to configure a domain for the Web Panel? (y/n): " -n 1 -r configure_domain
    echo
    local domain_arg=""
    if [[ $configure_domain =~ ^[Yy]$ ]]; then
         read -p "Enter domain name: " domain_name
    fi
    
    if [[ -n "$domain_name" ]]; then
         domain="$domain_name"
         # Check if domain resolves
         if ! getent hosts "$domain" > /dev/null 2>&1; then
             log_warning "Warning: The domain '$domain' does not resolve to an IP address."
             log_warning "You must configure DNS (A record) for this domain to point to this server."
             log_warning "If you don't own this domain, please reinstall and choose NOT to configure a domain to use IP."
             sleep 3
         fi
    else
         log_info "Detecting public IP..."
         domain=$(curl -s https://api.ipify.org || curl -s https://ifconfig.me)
         if [[ -z "$domain" ]]; then
             log_warning "Could not detect public IP. Using 'localhost'."
             domain="localhost"
         else
             log_info "Using public IP as domain: $domain"
         fi
    fi

    read -p "Enter port for Web Panel (default: 8080): " panel_port
    panel_port=${panel_port:-8080}
    
    # Generate random credentials
    local admin_user=$(pwgen -A -0 8 1) # Generate random 8-char username (no numbers/symbols for easier typing, if preferred, or just mixed)
    local admin_pass=$(pwgen -s 30 1)
    
    log_info "Installing Web Panel on port $panel_port..."
    
    if output=$(python3 core/cli.py webpanel -a start -d "$domain" -p "$panel_port" -au "$admin_user" -ap "$admin_pass" 2>&1); then
        log_success "Web Panel installed successfully."
        
        # Extract URL from output (it contains the secret path)
        local full_url=$(echo "$output" | grep -o "accessible on: .*" | awk '{print $3}')
        
        # Fallback if extraction failed for some reason
        if [[ -z "$full_url" ]]; then
             full_url=$(python3 core/cli.py get-webpanel-url --url-only)
        fi

        echo -e "\n${BOLD}${GREEN}Web Panel Credentials:${NC}"
        echo -e "URL: $full_url"
        echo -e "Username: ${YELLOW}$admin_user${NC}"
        echo -e "Password: ${YELLOW}$admin_pass${NC}\n"
        
        # Save credentials to a file for user reference
        echo "Web Panel Credentials:" > /etc/hysteria/webpanel_credentials.txt
        echo "URL: $full_url" >> /etc/hysteria/webpanel_credentials.txt
        echo "Username: $admin_user" >> /etc/hysteria/webpanel_credentials.txt
        echo "Password: $admin_pass" >> /etc/hysteria/webpanel_credentials.txt
        log_info "Credentials saved to /etc/hysteria/webpanel_credentials.txt"
    else
        log_error "Failed to install Web Panel."
        echo "$output"
    fi
}

add_alias() {
    log_info "Adding 'pany' alias to .bashrc..."
    
    if ! grep -q "alias pany='source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/menu.sh'" ~/.bashrc; then
        echo "alias pany='source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/menu.sh'" >> ~/.bashrc
        log_success "Added 'pany' alias to .bashrc"
    else
        log_info "Alias 'pany' already exists in .bashrc"
    fi
    
    # Remove old alias if it exists
    if grep -q "alias hys2=" ~/.bashrc; then
        sed -i '/alias hys2=/d' ~/.bashrc
    fi
}

run_menu() {
    log_info "Preparing to run menu..."
    
    cd /etc/hysteria || { log_error "Failed to change to /etc/hysteria directory"; exit 1; }
    chmod +x menu.sh || { log_error "Failed to make menu.sh executable"; exit 1; }
    
    log_info "Starting menu..."
    echo -e "\n${BOLD}${GREEN}======== Launching any Menu ========${NC}\n"
    ./menu.sh
}

main() {
    echo -e "\n${BOLD}${BLUE}======== any Setup Script ========${NC}\n"
    
    check_root
    check_os_version
    install_packages
    download_and_extract_release
    setup_python_env
    configure_hysteria
    configure_webpanel
    add_alias
    
    source ~/.bashrc &> /dev/null || true
    
    echo -e "\n${YELLOW}Installation complete! Press Enter to launch the menu...${NC}"
    read -r
    
    run_menu
}

main