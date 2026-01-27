#!/bin/bash

set -euo pipefail
trap 'echo -e "\n❌ An error occurred. Aborting."; exit 1' ERR

HYSTERIA_INSTALL_DIR="/etc/hysteria"
TEMP_DIR=$(mktemp -d)

GREEN=$(tput setaf 2)
RED=$(tput setaf 1)
BLUE=$(tput setaf 4)
RESET=$(tput sgr0)

info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] - ${RESET} $1"; }
success() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [OK] - ${RESET} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] - ${RESET} $1"; }

update_core() {
    local arch
    case $(uname -m) in
        x86_64) arch="amd64" ;;
        aarch64) arch="arm64" ;;
        *)
            error "Unsupported architecture: $(uname -m)"
            exit 1
            ;;
    esac
    info "Detected architecture: $arch"

    local zip_name="ANY-${arch}.zip"
    local download_url="https://github.com/0xd5f/ANY/releases/latest/download/${zip_name}"
    local temp_zip="$TEMP_DIR/${zip_name}"

    info "Downloading latest release from ${download_url}..."
    if ! curl -sL -o "$temp_zip" "$download_url"; then
        error "Failed to download the release asset. Please check the URL and your connection."
        exit 1
    fi
    success "Download complete."

    info "Extracting to temporary directory..."
    if ! unzip -q "$temp_zip" -d "$TEMP_DIR"; then
        error "Failed to extract the archive."
        exit 1
    fi
    
    info "Updating core directory..."
    if [ -d "$TEMP_DIR/core" ]; then
        cp -rf "$TEMP_DIR/core" "$HYSTERIA_INSTALL_DIR/"
        
        chmod -R +x "$HYSTERIA_INSTALL_DIR/core/scripts" || true
        chmod +x "$HYSTERIA_INSTALL_DIR/core/scripts/hysteria2/kick.py" || true
        chmod +x "$HYSTERIA_INSTALL_DIR/core/scripts/auth/user_auth" || true
        
        success "Core directory updated and permissions set."
    else
        error "Core directory not found in the downloaded release."
        exit 1
    fi
}

info "Starting lightweight upgrade (Core only)..."

update_core

info "Restarting services..."
systemctl restart hysteria-webpanel
systemctl restart hysteria-normal-sub.service

rm -rf "$TEMP_DIR"

success "🎉 Core upgrade completed successfully!"
