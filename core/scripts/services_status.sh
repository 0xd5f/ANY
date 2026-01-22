#!/bin/bash

declare -a services=(
    "hysteria-server.service"
    "hysteria-scheduler.service"
    "hysteria-auth.service"
    "hysteria-webpanel.service"
    "hysteria-caddy.service"
    "hysteria-telegram-bot.service"
    "hysteria-normal-sub.service"
    "hysteria-caddy-normalsub.service"
    "hysteria-ip-limit.service"
    "wg-quick@wgcf.service"
)

status_json="{"
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        status_json+="\"$service\":true,"
    else
        status_json+="\"$service\":false,"
    fi
done

status_json="${status_json%,}}"

echo "$status_json" | jq -M .
