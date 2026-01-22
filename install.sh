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
        echo -e "${YELLOW}bash <(curl -sL https://raw.githubusercontent.com/ReturnFI/any/nodb/install.sh)${NC}"
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
         if [[ -n "$domain_name" ]]; then
             domain_arg="--domain $domain_name"
         fi
    fi

    read -p "Enter port for Web Panel (default: 8080): " panel_port
    panel_port=${panel_port:-8080}
    
    # Generate random credentials
    local admin_user="admin"
    local admin_pass=$(pwgen -s 12 1)
    
    log_info "Installing Web Panel on port $panel_port..."
    if python3 core/cli.py install-webpanel --port "$panel_port" --username "$admin_user" --password "$admin_pass" $domain_arg; then
        log_success "Web Panel installed successfully."
        echo -e "\n${BOLD}${GREEN}Web Panel Credentials:${NC}"
        echo -e "URL: http://YOUR_IP:$panel_port (or https://$domain_name if configured)"
        echo -e "Username: ${YELLOW}$admin_user${NC}"
        echo -e "Password: ${YELLOW}$admin_pass${NC}\n"
        
        # Save credentials to a file for user reference
        echo "Web Panel Credentials:" > /etc/hysteria/webpanel_credentials.txt
        echo "Username: $admin_user" >> /etc/hysteria/webpanel_credentials.txt
        echo "Password: $admin_pass" >> /etc/hysteria/webpanel_credentials.txt
        log_info "Credentials saved to /etc/hysteria/webpanel_credentials.txt"
    else
        log_error "Failed to install Web Panel."
    fi
}

add_alias() {
    log_info "Adding 'hys2' alias to .bashrc..."
    
    if ! grep -q "alias hys2='source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/menu.sh'" ~/.bashrc; then
        echo "alias hys2='source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/menu.sh'" >> ~/.bashrc
        log_success "Added 'hys2' alias to .bashrc"
    else
        log_info "Alias 'hys2' already exists in .bashrc"
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
    
    echo -e "\n${YELLOW}Starting any in 3 seconds...${NC}"
    sleep 3
    
    run_menu
}

main