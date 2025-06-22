#!/bin/bash

# Telegram Bots Management Script
# Usage: ./scripts/telegram_bots.sh [command] [rickshaw_bot_id] [rickshaw_token] [metro_bot_id] [metro_token]
# Commands: start, stop, restart, status

# Check if we have the required arguments for bot operations
if [ "$1" != "status" ] && [ "$1" != "stop" ] && [ $# -lt 5 ]; then
    echo "Error: Missing bot configuration arguments"
    echo "Usage: $0 [command] [rickshaw_bot_id] [rickshaw_token] [metro_bot_id] [metro_token]"
    echo "For stop/status commands, bot credentials are not required"
    exit 1
fi

# Bot configurations from arguments
RICKSHAW_BOT_ID="$2"
RICKSHAW_TOKEN="$3"
METRO_BOT_ID="$4"
METRO_TOKEN="$5"

# PID file locations
RICKSHAW_PID_FILE="/tmp/rickshaw_bot.pid"
METRO_PID_FILE="/tmp/metro_bot.pid"

# Log file locations
RICKSHAW_LOG_FILE="logs/rickshaw_bot.log"
METRO_LOG_FILE="logs/metro_bot.log"

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to start a bot
start_bot() {
    local bot_name=$1
    local bot_id=$2
    local token=$3
    local pid_file=$4
    local log_file=$5
    
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "$bot_name is already running (PID: $(cat "$pid_file"))"
        return 1
    fi
    
    echo "Starting $bot_name..."
    nohup python3 telegram_app/telegram_bot.py "$bot_id" "$token" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    echo "$bot_name started with PID: $pid"
    echo "Logs: $log_file"
}

# Function to stop a bot
stop_bot() {
    local bot_name=$1
    local pid_file=$2
    
    if [ ! -f "$pid_file" ]; then
        echo "$bot_name is not running (no PID file found)"
        return 1
    fi
    
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Stopping $bot_name (PID: $pid)..."
        kill "$pid"
        sleep 2
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing $bot_name..."
            kill -9 "$pid"
        fi
        
        rm -f "$pid_file"
        echo "$bot_name stopped"
    else
        echo "$bot_name was not running"
        rm -f "$pid_file"
    fi
}

# Function to check bot status
check_status() {
    local bot_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "$bot_name is running (PID: $(cat "$pid_file"))"
        return 0
    else
        echo "$bot_name is not running"
        return 1
    fi
}

# Function to start all bots
start_all() {
    echo "Starting all Telegram bots..."
    start_bot "Rickshaw Coffee Digital Twin" "$RICKSHAW_BOT_ID" "$RICKSHAW_TOKEN" "$RICKSHAW_PID_FILE" "$RICKSHAW_LOG_FILE"
    start_bot "Metro Farm Digital Twin" "$METRO_BOT_ID" "$METRO_TOKEN" "$METRO_PID_FILE" "$METRO_LOG_FILE"
}

# Function to stop all bots
stop_all() {
    echo "Stopping all Telegram bots..."
    stop_bot "Rickshaw Coffee Digital Twin" "$RICKSHAW_PID_FILE"
    stop_bot "Metro Farm Digital Twin" "$METRO_PID_FILE"
}

# Function to show status of all bots
status_all() {
    echo "Telegram Bots Status:"
    echo "====================="
    check_status "Rickshaw Coffee Digital Twin" "$RICKSHAW_PID_FILE"
    check_status "Metro Farm Digital Twin" "$METRO_PID_FILE"
}

# Function to restart all bots
restart_all() {
    echo "Restarting all Telegram bots..."
    stop_all
    sleep 3
    start_all
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [rickshaw_bot_id] [rickshaw_token] [metro_bot_id] [metro_token]"
    echo ""
    echo "Commands:"
    echo "  start   - Start both Telegram bots"
    echo "  stop    - Stop both Telegram bots (no credentials needed)"
    echo "  restart - Restart both Telegram bots"
    echo "  status  - Show status of both bots (no credentials needed)"
    echo ""
    echo "Examples:"
    echo "  # Start both bots"
    echo "  $0 start <rickshaw_bot_id> <rickshaw_token> <metro_bot_id> <metro_token>"
    echo ""
    echo "  # Stop both bots"
    echo "  $0 stop"
    echo ""
    echo "  # Check status"
    echo "  $0 status"
    echo ""
    echo "Log files:"
    echo "  Rickshaw Coffee: $RICKSHAW_LOG_FILE"
    echo "  Metro Farm: $METRO_LOG_FILE"
}

# Main script logic
case "$1" in
    start)
        if [ $# -lt 5 ]; then
            echo "Error: Bot credentials required for start command"
            show_usage
            exit 1
        fi
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        if [ $# -lt 5 ]; then
            echo "Error: Bot credentials required for restart command"
            show_usage
            exit 1
        fi
        restart_all
        ;;
    status)
        status_all
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
