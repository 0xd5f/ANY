#!/bin/bash
source /etc/hysteria/core/scripts/utils.sh
define_colors

CADDY_CONFIG_FILE_NORMALSUB="/etc/hysteria/core/scripts/normalsub/Caddyfile.normalsub"
NORMALSUB_ENV_FILE="/etc/hysteria/core/scripts/normalsub/.env"
DEFAULT_AIOHTTP_LISTEN_ADDRESS="127.0.0.1"
DEFAULT_AIOHTTP_LISTEN_PORT="28261"

install_caddy_if_needed() {
    if command -v caddy &> /dev/null; then
        echo -e "${green}Caddy is already installed.${NC}"
        if systemctl list-units --full -all | grep -q 'caddy.service'; then
            if systemctl is-active --quiet caddy.service; then
                echo -e "${yellow}Stopping and disabling default caddy.service...${NC}"
                systemctl stop caddy > /dev/null 2>&1
                systemctl disable caddy > /dev/null 2>&1
            fi
        fi
        return 0
    fi

    echo -e "${yellow}Installing Caddy...${NC}"
    sudo apt update -y > /dev/null 2>&1
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl > /dev/null 2>&1

    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg > /dev/null 2>&1
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null 2>&1
    chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    chmod o+r /etc/apt/sources.list.d/caddy-stable.list

    sudo apt update -y > /dev/null 2>&1
    sudo apt install -y caddy
    if [ $? -ne 0 ]; then
        echo -e "${red}Error: Failed to install Caddy. ${NC}"
        exit 1
    fi
    systemctl stop caddy > /dev/null 2>&1
    systemctl disable caddy > /dev/null 2>&1
    echo -e "${green}Caddy installed successfully. ${NC}"
}

update_env_file() {
    local domain=$1
    local external_port=$2
    local aiohttp_listen_address=$3
    local aiohttp_listen_port=$4
    local subpath_val=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 32)

    cat <<EOL > "$NORMALSUB_ENV_FILE"
HYSTERIA_DOMAIN=$domain
HYSTERIA_PORT=$external_port
AIOHTTP_LISTEN_ADDRESS=$aiohttp_listen_address
AIOHTTP_LISTEN_PORT=$aiohttp_listen_port
SUBPATH=$subpath_val
EOL
}

update_caddy_file_normalsub() {
    local domain=$1
    local external_port=$2
    local subpath_val=$3
    local aiohttp_address=$4
    local aiohttp_port=$5

    cat <<EOL > "$CADDY_CONFIG_FILE_NORMALSUB"
{
    admin off
    auto_https disable_redirects
}

$domain:$external_port {
    encode gzip zstd
    
    route /$subpath_val/* {
        reverse_proxy $aiohttp_address:$aiohttp_port {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Port {server_port}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    @blocked {
        not path /$subpath_val/*
    }
    abort @blocked
}
EOL
}

create_normalsub_python_service_file() {
    cat <<EOL > /etc/systemd/system/hysteria-normal-sub.service
[Unit]
Description=Hysteria Normalsub Python Service
After=network.target

[Service]
ExecStart=/bin/bash -c 'source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/hysteria2_venv/bin/python /etc/hysteria/core/scripts/normalsub/normalsub.py'
WorkingDirectory=/etc/hysteria/core/scripts/normalsub
EnvironmentFile=$NORMALSUB_ENV_FILE
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOL
}

create_caddy_normalsub_service_file() {
    cat <<EOL > /etc/systemd/system/hysteria-caddy-normalsub.service
[Unit]
Description=Caddy for Hysteria Normalsub
After=network.target

[Service]
WorkingDirectory=/etc/hysteria/core/scripts/normalsub
ExecStart=/usr/bin/caddy run --environ --config $CADDY_CONFIG_FILE_NORMALSUB
ExecReload=/usr/bin/caddy reload --config $CADDY_CONFIG_FILE_NORMALSUB --force
TimeoutStopSec=5s
LimitNOFILE=1048576
PrivateTmp=true
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOL
}

start_service() {
    local domain=$1
    local external_port=$2

    install_caddy_if_needed

    local aiohttp_listen_address="$DEFAULT_AIOHTTP_LISTEN_ADDRESS"
    local aiohttp_listen_port="$DEFAULT_AIOHTTP_LISTEN_PORT"

    update_env_file "$domain" "$external_port" "$aiohttp_listen_address" "$aiohttp_listen_port"
    source "$NORMALSUB_ENV_FILE" 

    update_caddy_file_normalsub "$HYSTERIA_DOMAIN" "$HYSTERIA_PORT" "$SUBPATH" "$AIOHTTP_LISTEN_ADDRESS" "$AIOHTTP_LISTEN_PORT"
    
    create_normalsub_python_service_file
    create_caddy_normalsub_service_file

    systemctl daemon-reload
    
    systemctl enable hysteria-normal-sub.service > /dev/null 2>&1
    systemctl start hysteria-normal-sub.service
    
    systemctl enable hysteria-caddy-normalsub.service > /dev/null 2>&1
    systemctl start hysteria-caddy-normalsub.service

    if systemctl is-active --quiet hysteria-normal-sub.service && systemctl is-active --quiet hysteria-caddy-normalsub.service; then
        echo -e "${green}Normalsub service setup completed.${NC}"
        echo -e "${green}Access base URL: https://$HYSTERIA_DOMAIN:$HYSTERIA_PORT/$SUBPATH/{username}${NC}"
    else
        echo -e "${red}Normalsub setup completed, but one or more services failed to start.${NC}"
        systemctl status hysteria-normal-sub.service --no-pager
        systemctl status hysteria-caddy-normalsub.service --no-pager
    fi
}

stop_service() {
    echo -e "${yellow}Stopping Hysteria Normalsub Python service...${NC}"
    systemctl stop hysteria-normal-sub.service > /dev/null 2>&1
    systemctl disable hysteria-normal-sub.service > /dev/null 2>&1
    echo -e "${yellow}Stopping Caddy service for Normalsub...${NC}"
    systemctl stop hysteria-caddy-normalsub.service > /dev/null 2>&1
    systemctl disable hysteria-caddy-normalsub.service > /dev/null 2>&1
    
    systemctl daemon-reload > /dev/null 2>&1

    rm -f "$NORMALSUB_ENV_FILE"
    rm -f "$CADDY_CONFIG_FILE_NORMALSUB"
    rm -f /etc/systemd/system/hysteria-normal-sub.service
    rm -f /etc/systemd/system/hysteria-caddy-normalsub.service
    systemctl daemon-reload > /dev/null 2>&1

    echo -e "${green}Normalsub services stopped and disabled. Configuration files removed.${NC}"
}

edit_subpath() {
    local new_path="$1"
    
    if [ ! -f "$NORMALSUB_ENV_FILE" ]; then
        echo -e "${red}Error: .env file ($NORMALSUB_ENV_FILE) not found. Please run the start command first.${NC}"
        exit 1
    fi

    if [[ ! "$new_path" =~ ^[a-zA-Z0-9]+(/[a-zA-Z0-9]+)*$ ]]; then
        echo -e "${red}Error: Invalid subpath format. Must be alphanumeric segments separated by single slashes (e.g., 'path' or 'path/to/resource'). Cannot start/end with a slash or have consecutive slashes.${NC}"
        exit 1
    fi

    if ! systemctl is-active --quiet hysteria-normal-sub.service || ! systemctl is-active --quiet hysteria-caddy-normalsub.service; then
        echo -e "${red}Error: One or more services are not running. Please start the services first.${NC}"
        exit 1
    fi

    source "$NORMALSUB_ENV_FILE"
    local old_subpath="$SUBPATH"
    
    sed -i "s|^SUBPATH=.*|SUBPATH=$new_path|" "$NORMALSUB_ENV_FILE"
    echo -e "${green}SUBPATH updated from '$old_subpath' to '$new_path' in $NORMALSUB_ENV_FILE.${NC}"

    update_caddy_file_normalsub "$HYSTERIA_DOMAIN" "$HYSTERIA_PORT" "$new_path" "$AIOHTTP_LISTEN_ADDRESS" "$AIOHTTP_LISTEN_PORT"
    echo -e "${green}Caddyfile for Normalsub updated with new subpath.${NC}"

    echo -e "${yellow}Restarting hysteria-normal-sub service to reload environment...${NC}"
    systemctl restart hysteria-normal-sub.service

    echo -e "${yellow}Reloading Caddy configuration...${NC}"
    if systemctl reload hysteria-caddy-normalsub.service 2>/dev/null; then
        echo -e "${green}Caddy configuration reloaded successfully.${NC}"
    else
        echo -e "${yellow}Reload failed, restarting Caddy service...${NC}"
        systemctl restart hysteria-caddy-normalsub.service
    fi

    if systemctl is-active --quiet hysteria-normal-sub.service && systemctl is-active --quiet hysteria-caddy-normalsub.service; then
        echo -e "${green}Services updated successfully.${NC}"
        echo -e "${green}New access base URL: https://$HYSTERIA_DOMAIN:$HYSTERIA_PORT/$new_path/{username}${NC}"
        echo -e "${cyan}Old subpath '$old_subpath' is no longer accessible.${NC}"
    else
        echo -e "${red}Error: One or more services failed to restart/reload. Please check logs.${NC}"
        systemctl status hysteria-normal-sub.service --no-pager
        systemctl status hysteria-caddy-normalsub.service --no-pager
    fi
}

edit_profile_title() {
    local new_title="$1"
    
    if [ ! -f "$NORMALSUB_ENV_FILE" ]; then
        echo -e "${red}Error: .env file ($NORMALSUB_ENV_FILE) not found. Please run the start command first.${NC}"
        exit 1
    fi

    if [ -z "$new_title" ]; then
        echo -e "${red}Error: New profile title cannot be empty.${NC}"
        exit 1
    fi

    if grep -q "^PROFILE_TITLE=" "$NORMALSUB_ENV_FILE"; then
         sed -i "s|^PROFILE_TITLE=.*|PROFILE_TITLE=$new_title|" "$NORMALSUB_ENV_FILE"
    else
         echo "PROFILE_TITLE=$new_title" >> "$NORMALSUB_ENV_FILE"
    fi
    
    echo -e "${green}PROFILE_TITLE updated to '$new_title' in $NORMALSUB_ENV_FILE.${NC}"

    echo -e "${yellow}Restarting hysteria-normal-sub service to reload environment...${NC}"
    systemctl restart hysteria-normal-sub.service
    
    if systemctl is-active --quiet hysteria-normal-sub.service; then
        echo -e "${green}Service updated successfully.${NC}"
    else
        echo -e "${red}Error: Service failed to restart. Please check logs.${NC}"
        systemctl status hysteria-normal-sub.service --no-pager
    fi
}

edit_show_username() {
    local val=$1
    if [ ! -f "$NORMALSUB_ENV_FILE" ]; then
        echo -e "${red}Error: .env file ($NORMALSUB_ENV_FILE) not found.${NC}"
        exit 1
    fi
    
    if grep -q "^SHOW_USERNAME=" "$NORMALSUB_ENV_FILE"; then
         sed -i "s|^SHOW_USERNAME=.*|SHOW_USERNAME=$val|" "$NORMALSUB_ENV_FILE"
    else
         echo "SHOW_USERNAME=$val" >> "$NORMALSUB_ENV_FILE"
    fi
    
    echo -e "${yellow}Restarting hysteria-normal-sub service...${NC}"
    systemctl restart hysteria-normal-sub.service
}

edit_support_url() {
    local val=$1
    if [ ! -f "$NORMALSUB_ENV_FILE" ]; then
        echo -e "${red}Error: .env file ($NORMALSUB_ENV_FILE) not found.${NC}"
        exit 1
    fi
    
    if grep -q "^SUPPORT_URL=" "$NORMALSUB_ENV_FILE"; then
         sed -i "s|^SUPPORT_URL=.*|SUPPORT_URL=$val|" "$NORMALSUB_ENV_FILE"
    else
         echo "SUPPORT_URL=$val" >> "$NORMALSUB_ENV_FILE"
    fi
    
    echo -e "${yellow}Restarting hysteria-normal-sub service...${NC}"
    systemctl restart hysteria-normal-sub.service
}

case "$1" in
    start)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${red}Usage: $0 start <EXTERNAL_DOMAIN> <EXTERNAL_PORT>${NC}"
            exit 1
        fi
        start_service "$2" "$3"
        ;;
    stop)
        stop_service
        ;;
    edit_subpath)
        if [ -z "$2" ]; then
            echo -e "${red}Usage: $0 edit_subpath <NEW_SUBPATH>${NC}"
            exit 1
        fi
        edit_subpath "$2"
        ;;
    edit_profile_title)
        if [ -z "$2" ]; then
            echo -e "${red}Usage: $0 edit_profile_title <NEW_TITLE>${NC}"
            exit 1
        fi
        edit_profile_title "$2"
        ;;
    edit_show_username)
        if [ -z "$2" ]; then
            echo -e "${red}Usage: $0 edit_show_username <true|false>${NC}"
            exit 1
        fi
        edit_show_username "$2"
        ;;
    edit_support_url)
        edit_support_url "$2"
        ;;
    *)
        echo -e "${red}Usage: $0 {start <EXTERNAL_DOMAIN> <EXTERNAL_PORT> | stop | edit_subpath <NEW_SUBPATH> | edit_profile_title <NEW_TITLE> | edit_support_url <URL>}${NC}"
        exit 1
        ;;
esac