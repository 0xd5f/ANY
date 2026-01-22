#!/bin/bash
source /etc/hysteria/core/scripts/utils.sh
define_colors

CADDY_CONFIG_FILE="/etc/hysteria/core/scripts/webpanel/Caddyfile"
WEBPANEL_ENV_FILE="/etc/hysteria/core/scripts/webpanel/.env"

install_dependencies() {
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
    sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl libnss3-tools > /dev/null 2>&1

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
    local port=$2
    local admin_username=$3
    local admin_password=$4
    local admin_password_hash=$(echo -n "$admin_password" | sha256sum | cut -d' ' -f1) # hash the password
    local expiration_minutes=$5
    local debug=$6
    local decoy_path=$7

    local api_token=$(openssl rand -hex 32) 
    local root_path=$(openssl rand -hex 16)

    cat <<EOL > /etc/hysteria/core/scripts/webpanel/.env
DEBUG=$debug
DOMAIN=$domain
PORT=$port
ROOT_PATH=$root_path
API_TOKEN=$api_token
ADMIN_USERNAME=$admin_username
ADMIN_PASSWORD=$admin_password_hash
EXPIRATION_MINUTES=$expiration_minutes
EOL

    if [ -n "$decoy_path" ] && [ "$decoy_path" != "None" ]; then
        echo "DECOY_PATH=$decoy_path" >> /etc/hysteria/core/scripts/webpanel/.env
    fi
}

update_caddy_file() {
    source /etc/hysteria/core/scripts/webpanel/.env
    
    if [ -z "$DOMAIN" ] || [ -z "$PORT" ]; then
        echo -e "${red}Error: One or more environment variables are missing.${NC}"
        return 1
    fi

    if [ -z "$ROOT_PATH" ] || [ "$ROOT_PATH" == "/" ]; then
        cat <<EOL > "$CADDY_CONFIG_FILE"
{
    admin off
    auto_https disable_redirects
}

$DOMAIN:$PORT {
    reverse_proxy http://127.0.0.1:28260
}
EOL
        return 0
    fi

    if [ -n "$DECOY_PATH" ] && [ "$DECOY_PATH" != "None" ] && [ "$PORT" -eq 443 ]; then
        cat <<EOL > "$CADDY_CONFIG_FILE"
{
    admin off
    auto_https disable_redirects
}

$DOMAIN:$PORT {
    route /$ROOT_PATH/* {

        reverse_proxy http://127.0.0.1:28260
    }
    
    @otherPaths {
        not path /$ROOT_PATH/*
    }
    
    handle @otherPaths {
        root * $DECOY_PATH
        file_server
    }
}
EOL
    else
        cat <<EOL > "$CADDY_CONFIG_FILE"
{
    admin off
    auto_https disable_redirects
}

$DOMAIN:$PORT {
    route /$ROOT_PATH/* {
        reverse_proxy http://127.0.0.1:28260
    }
    
    @blocked {
        not path /$ROOT_PATH/*
    }
    
    abort @blocked
}
EOL

        if [ -n "$DECOY_PATH" ] && [ "$DECOY_PATH" != "None" ] && [ "$PORT" -ne 443 ]; then
            cat <<EOL >> "$CADDY_CONFIG_FILE"

$DOMAIN:443 {
    root * $DECOY_PATH
    file_server
}
EOL
        fi
    fi
}

create_webpanel_service_file() {
    cat <<EOL > /etc/systemd/system/hysteria-webpanel.service
[Unit]
Description=Hysteria2 Web Panel
After=network.target

[Service]
WorkingDirectory=/etc/hysteria/core/scripts/webpanel
EnvironmentFile=/etc/hysteria/core/scripts/webpanel/.env
ExecStart=/bin/bash -c 'source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/hysteria2_venv/bin/python /etc/hysteria/core/scripts/webpanel/app.py'
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOL
}

create_caddy_service_file() {
    cat <<EOL > /etc/systemd/system/hysteria-caddy.service
[Unit]
Description=Hysteria2 Caddy
After=network.target

[Service]
WorkingDirectory=/etc/caddy
ExecStart=/usr/bin/caddy run --environ --config $CADDY_CONFIG_FILE
ExecReload=/usr/bin/caddy reload --config $CADDY_CONFIG_FILE --force
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
    local port=$2
    local admin_username=$3
    local admin_password=$4
    local expiration_minutes=$5
    local debug=$6
    local decoy_path=$7 

    install_dependencies

    update_env_file "$domain" "$port" "$admin_username" "$admin_password" "$expiration_minutes" "$debug" "$decoy_path"
    if [ $? -ne 0 ]; then
        echo -e "${red}Error: Failed to update the environment file.${NC}"
        return 1
    fi

    create_webpanel_service_file
    if [ $? -ne 0 ]; then
        echo -e "${red}Error: Failed to create the webpanel service file.${NC}"
        return 1
    fi

    systemctl daemon-reload
    systemctl enable hysteria-webpanel.service > /dev/null 2>&1
    systemctl start hysteria-webpanel.service > /dev/null 2>&1

    if systemctl is-active --quiet hysteria-webpanel.service; then
        echo -e "${green}Hysteria web panel setup completed. The web panel is running locally on: http://127.0.0.1:28260/${NC}"
    else
        echo -e "${red}Error: Hysteria web panel service failed to start.${NC}"
        return 1
    fi

    update_caddy_file
    if [ $? -ne 0 ]; then
        echo -e "${red}Error: Failed to update the Caddyfile.${NC}"
        return 1
    fi

    create_caddy_service_file
    if [ $? -ne 0 ]; then
        echo -e "${red}Error: Failed to create the Caddy service file.${NC}"
        return 1
    fi

    systemctl daemon-reload
    systemctl enable hysteria-caddy.service 
    systemctl start hysteria-caddy.service
    if [ $? -ne 0 ]; then
        echo -e "${red}Error: Failed to restart Caddy.${NC}"
        return 1
    fi

    if systemctl is-active --quiet hysteria-webpanel.service; then
        source /etc/hysteria/core/scripts/webpanel/.env
        local webpanel_url="http://$domain:$port/$ROOT_PATH/"
        echo -e "${green}Hysteria web panel is now running. The service is accessible on: $webpanel_url ${NC}"
        
        if [ -n "$DECOY_PATH" ] && [ "$DECOY_PATH" != "None" ]; then
            if [ "$port" -eq 443 ]; then
                echo -e "${green}Decoy site is configured on the same port (443) and will handle non-webpanel paths.${NC}"
            else
                echo -e "${green}Decoy site is configured on port 443 at: http://$domain:443/${NC}"
            fi
        fi
    else
        echo -e "${red}Error: Hysteria web panel failed to start after Caddy restart.${NC}"
    fi
}

setup_decoy_site() {
    local domain=$1
    local decoy_path=$2
    
    if [ -z "$domain" ] || [ -z "$decoy_path" ]; then
        echo -e "${red}Usage: $0 decoy <DOMAIN> <PATH_TO_DECOY_SITE>${NC}"
        return 1
    fi
    
    if [ ! -d "$decoy_path" ]; then
        echo -e "${yellow}Warning: Decoy site path does not exist. Creating directory...${NC}"
        mkdir -p "$decoy_path"
        echo "<html><body><h1>Website Under Construction</h1></body></html>" > "$decoy_path/index.html"
    fi
    
    if [ -f "/etc/hysteria/core/scripts/webpanel/.env" ]; then
        source /etc/hysteria/core/scripts/webpanel/.env
        sed -i "/DECOY_PATH=/d" /etc/hysteria/core/scripts/webpanel/.env
        echo "DECOY_PATH=$decoy_path" >> /etc/hysteria/core/scripts/webpanel/.env
        
        update_caddy_file
        
        systemctl restart hysteria-caddy.service
        
        echo -e "${green}Decoy site configured successfully for $domain${NC}"
        if [ "$PORT" -eq 443 ]; then
            echo -e "${green}Decoy site is accessible at non-webpanel paths on: https://$domain:443/${NC}"
        else
            echo -e "${green}Decoy site is accessible at: https://$domain:443/${NC}"
        fi
    else
        echo -e "${red}Error: Web panel is not configured yet. Please start the web panel first.${NC}"
        return 1
    fi
}

stop_decoy_site() {
    if [ ! -f "/etc/hysteria/core/scripts/webpanel/.env" ]; then
        echo -e "${red}Error: Web panel is not configured.${NC}"
        return 1
    fi
    
    source /etc/hysteria/core/scripts/webpanel/.env
    
    if [ -z "$DECOY_PATH" ] || [ "$DECOY_PATH" = "None" ]; then
        echo -e "${yellow}No decoy site is currently configured.${NC}"
        return 0
    fi
    
    local was_separate_port=false
    if [ "$PORT" -ne 443 ]; then
        was_separate_port=true
    fi
    
    sed -i "/DECOY_PATH=/d" /etc/hysteria/core/scripts/webpanel/.env
    
    cat <<EOL > "$CADDY_CONFIG_FILE"
{
    admin off
    auto_https disable_redirects
}

$DOMAIN:$PORT {
    route /$ROOT_PATH/* {
        reverse_proxy http://127.0.0.1:28260
    }
    
    @blocked {
        not path /$ROOT_PATH/*
    }
    
    abort @blocked
}
EOL
    
    systemctl restart hysteria-caddy.service
    
    echo -e "${green}Decoy site has been stopped and removed from configuration.${NC}"
    if [ "$was_separate_port" = true ]; then
        echo -e "${green}Port 443 is no longer served by Caddy.${NC}"
    else
        echo -e "${green}Non-webpanel paths on port 443 will now return connection errors instead of serving the decoy site.${NC}"
    fi
}

reset_credentials() {
    local new_username_val=""
    local new_password_val=""
    local changes_made=false

    if [ ! -f "$WEBPANEL_ENV_FILE" ]; then
        echo -e "${red}Error: Web panel .env file not found. Is the web panel configured?${NC}"
        exit 1
    fi

    OPTIND=1 
    while getopts ":u:p:" opt; do
        case $opt in
            u) new_username_val="$OPTARG" ;;
            p) new_password_val="$OPTARG" ;;
            \?) echo -e "${red}Invalid option: -$OPTARG${NC}" >&2; exit 1 ;;
            :) echo -e "${red}Option -$OPTARG requires an argument.${NC}" >&2; exit 1 ;;
        esac
    done

    if [ -z "$new_username_val" ] && [ -z "$new_password_val" ]; then
        echo -e "${red}Error: At least one option (-u <new_username> or -p <new_password>) must be provided.${NC}"
        echo -e "${yellow}Usage: $0 resetcreds [-u new_username] [-p new_password]${NC}"
        exit 1
    fi

    if [ -n "$new_username_val" ]; then
        echo "Updating username to: $new_username_val"
        if sudo sed -i "s|^ADMIN_USERNAME=.*|ADMIN_USERNAME=$new_username_val|" "$WEBPANEL_ENV_FILE"; then
            changes_made=true
        else
            echo -e "${red}Failed to update username in $WEBPANEL_ENV_FILE${NC}"
            exit 1
        fi
    fi

    if [ -n "$new_password_val" ]; then
        echo "Updating password..."
        local new_password_hash=$(echo -n "$new_password_val" | sha256sum | cut -d' ' -f1)
        if sudo sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$new_password_hash|" "$WEBPANEL_ENV_FILE"; then
            changes_made=true
        else
             echo -e "${red}Failed to update password in $WEBPANEL_ENV_FILE${NC}"
             exit 1
        fi
    fi

    if [ "$changes_made" = true ]; then
        echo "Scheduling web panel restart..."
        (sleep 3 && systemctl restart hysteria-webpanel.service) > /dev/null 2>&1 &
        
        echo -e "${green}Web panel credentials updated successfully. Service will restart in 3 seconds.${NC}"
    else
        echo -e "${yellow}No changes were specified.${NC}"
    fi
}

change_expiration() {
    local new_expiration=$1

    if [ -z "$new_expiration" ]; then
        echo -e "${red}Usage: $0 changeexp <NEW_EXPIRATION_MINUTES>${NC}"
        exit 1
    fi

    if [ ! -f "$WEBPANEL_ENV_FILE" ]; then
        echo -e "${red}Error: Web panel .env file not found. Is the web panel configured?${NC}"
        exit 1
    fi

    echo "Updating session expiration to: $new_expiration minutes"
    if sudo sed -i "s|^EXPIRATION_MINUTES=.*|EXPIRATION_MINUTES=$new_expiration|" "$WEBPANEL_ENV_FILE"; then
        echo "Restarting web panel service to apply changes..."
        if systemctl restart hysteria-webpanel.service; then
            echo -e "${green}Web panel session expiration updated successfully.${NC}"
        else
            echo -e "${red}Failed to restart hysteria-webpanel service. Please restart it manually.${NC}"
        fi
    else
        echo -e "${red}Failed to update expiration in $WEBPANEL_ENV_FILE${NC}"
        exit 1
    fi
}

set_telegram_auth() {
    local enabled=$1

    if [ -z "$enabled" ]; then
        echo -e "${red}Usage: $0 settelegramauth <true|false>${NC}"
        exit 1
    fi

    if [ ! -f "$WEBPANEL_ENV_FILE" ]; then
        echo -e "${red}Error: Web panel .env file not found.${NC}"
        exit 1
    fi

    if ! grep -q "TELEGRAM_AUTH_ENABLED=" "$WEBPANEL_ENV_FILE"; then
        echo "TELEGRAM_AUTH_ENABLED=$enabled" | sudo tee -a "$WEBPANEL_ENV_FILE" > /dev/null
    else
        sudo sed -i "s|^TELEGRAM_AUTH_ENABLED=.*|TELEGRAM_AUTH_ENABLED=$enabled|" "$WEBPANEL_ENV_FILE"
    fi
    
    echo "Scheduling web panel restart..."
    (sleep 3 && systemctl restart hysteria-webpanel.service) > /dev/null 2>&1 &
    
    echo -e "${green}Telegram auth setting updated to $enabled. Service will restart in 3 seconds.${NC}"
}

change_root_path() {
    local new_root_path=$1

    if [ ! -f "$WEBPANEL_ENV_FILE" ]; then
        echo -e "${red}Error: Web panel .env file not found. Is the web panel configured?${NC}"
        exit 1
    fi

    if [ -z "$new_root_path" ] || [ "$new_root_path" == "random" ]; then
        echo "Generating a new random root path..."
        new_root_path=$(openssl rand -hex 16)
    elif [ "$new_root_path" == "off" ] || [ "$new_root_path" == "root" ] || [ "$new_root_path" == "/" ]; then
        echo "Disabling custom root path (Serving at /)..."
        new_root_path=""
    fi

    echo "Updating root path to: $new_root_path"
    if sudo sed -i "s|^ROOT_PATH=.*|ROOT_PATH=$new_root_path|" "$WEBPANEL_ENV_FILE"; then
        echo "Updating Caddy configuration..."
        update_caddy_file
        if [ $? -ne 0 ]; then
            echo -e "${red}Error: Failed to update the Caddyfile.${NC}"
            exit 1
        fi

        echo "Restarting services to apply changes..."
        if systemctl restart hysteria-webpanel.service && systemctl restart hysteria-caddy.service; then
            echo -e "${green}Web panel root path updated successfully.${NC}"
            echo -n "New URL: "
            show_webpanel_url
        else
            echo -e "${red}Failed to restart services. Please restart them manually.${NC}"
        fi
    else
        echo -e "${red}Failed to update root path in $WEBPANEL_ENV_FILE${NC}"
        exit 1
    fi
}

change_port_domain() {
    local new_domain=""
    local new_port=""
    local changes_made=false

    if [ ! -f "$WEBPANEL_ENV_FILE" ]; then
        echo -e "${red}Error: Web panel .env file not found. Is the web panel configured?${NC}"
        exit 1
    fi

    OPTIND=1
    while getopts ":d:p:" opt; do
        case $opt in
            d) new_domain="$OPTARG" ;;
            p) new_port="$OPTARG" ;;
            \?) echo -e "${red}Invalid option: -$OPTARG${NC}" >&2; exit 1 ;;
            :) echo -e "${red}Option -$OPTARG requires an argument.${NC}" >&2; exit 1 ;;
        esac
    done

    if [ -z "$new_domain" ] && [ -z "$new_port" ]; then
        echo -e "${red}Error: At least one option (-d <new_domain> or -p <new_port>) must be provided.${NC}"
        echo -e "${yellow}Usage: $0 changedomain [-d new_domain] [-p new_port]${NC}"
        exit 1
    fi

    if [ -n "$new_domain" ]; then
        echo "Updating domain to: $new_domain"
        if sudo sed -i "s|^DOMAIN=.*|DOMAIN=$new_domain|" "$WEBPANEL_ENV_FILE"; then
            changes_made=true
        else
            echo -e "${red}Failed to update domain in $WEBPANEL_ENV_FILE${NC}"
            exit 1
        fi
    fi

    if [ -n "$new_port" ]; then
        echo "Updating port to: $new_port"
        if sudo sed -i "s|^PORT=.*|PORT=$new_port|" "$WEBPANEL_ENV_FILE"; then
            changes_made=true
        else
            echo -e "${red}Failed to update port in $WEBPANEL_ENV_FILE${NC}"
            exit 1
        fi
    fi

    if [ "$changes_made" = true ]; then
        echo "Updating Caddy configuration..."
        update_caddy_file
        if [ $? -ne 0 ]; then
            echo -e "${red}Error: Failed to update the Caddyfile.${NC}"
            exit 1
        fi

        echo "Restarting Caddy service to apply changes..."
        if systemctl restart hysteria-caddy.service; then
            echo -e "${green}Web panel domain/port updated successfully.${NC}"
            echo -n "New URL: "
            show_webpanel_url
        else
            echo -e "${red}Failed to restart Caddy. Please restart it manually.${NC}"
        fi
    else
        echo -e "${yellow}No changes were made.${NC}"
    fi
}

show_webpanel_url() {
    source /etc/hysteria/core/scripts/webpanel/.env
    local protocol="https"
    # Check if DOMAIN is an IP address
    if [[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        protocol="http"
    fi
    local webpanel_url="${protocol}://$DOMAIN:$PORT/$ROOT_PATH/"
    echo "$webpanel_url"
}

show_webpanel_api_token() {
    source /etc/hysteria/core/scripts/webpanel/.env
    echo "$API_TOKEN"
}

stop_service() {
    echo "Stopping Caddy..."
    systemctl disable hysteria-caddy.service > /dev/null 2>&1
    systemctl stop hysteria-caddy.service > /dev/null 2>&1
    echo "Caddy stopped."
    
    echo "Stopping Hysteria web panel..."
    systemctl disable hysteria-webpanel.service > /dev/null 2>&1
    systemctl stop hysteria-webpanel.service > /dev/null 2>&1
    echo "Hysteria web panel stopped."

    systemctl daemon-reload
    rm -f /etc/hysteria/core/scripts/webpanel/.env
    rm -f "$CADDY_CONFIG_FILE"
}

case "$1" in
    start)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${red}Usage: $0 start <DOMAIN> <PORT> [ADMIN_USERNAME] [ADMIN_PASSWORD] [EXPIRATION_MINUTES] [DEBUG] [DECOY_PATH]${NC}"
            exit 1
        fi
        start_service "$2" "$3" "$4" "$5" "$6" "$7" "$8"
        ;;
    stop)
        stop_service
        ;;
    decoy)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${red}Usage: $0 decoy <DOMAIN> <PATH_TO_DECOY_SITE>${NC}"
            exit 1
        fi
        setup_decoy_site "$2" "$3"
        ;;
    stopdecoy)
        stop_decoy_site
        ;;
    resetcreds)
        shift 
        reset_credentials "$@"
        ;;
    changeexp)
        change_expiration "$2"
        ;;
    settelegramauth)
        set_telegram_auth "$2"
        ;;
    changeroot)
        change_root_path "$2"
        ;;
    changedomain)
        shift
        change_port_domain "$@"
        ;;
    url)
        show_webpanel_url
        ;;
    api-token)
        show_webpanel_api_token
        ;;
    *)
        echo -e "${red}Usage: $0 {start|stop|decoy|stopdecoy|resetcreds|changeexp|changeroot|changedomain|url|api-token} [options]${NC}"
        echo -e "${yellow}start <DOMAIN> <PORT> [ADMIN_USERNAME] [ADMIN_PASSWORD] [EXPIRATION_MINUTES] [DEBUG] [DECOY_PATH]${NC}"
        echo -e "${yellow}stop${NC}"
        echo -e "${yellow}decoy <DOMAIN> <PATH_TO_DECOY_SITE>${NC}"
        echo -e "${yellow}stopdecoy${NC}"
        echo -e "${yellow}resetcreds [-u new_username] [-p new_password]${NC}"
        echo -e "${yellow}changeexp <NEW_EXPIRATION_MINUTES>${NC}"
        echo -e "${yellow}changeroot [NEW_ROOT_PATH|off|random] # Generates random if not provided, use 'off' to disable${NC}"
        echo -e "${yellow}changedomain [-d new_domain] [-p new_port]${NC}"
        echo -e "${yellow}url${NC}"
        echo -e "${yellow}api-token${NC}"
        exit 1
        ;;
esac