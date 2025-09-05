#!/bin/bash
# Setup daily cron job for Personal News

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up daily Personal News cron job..."
echo "Current directory: $SCRIPT_DIR"

# Find uv path
UV_PATH=$(which uv)
if [ -z "$UV_PATH" ]; then
    echo "Error: uv not found in PATH"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Found uv at: $UV_PATH"

# Default time
DEFAULT_TIME="8:00"
read -p "What time should the newsletter be sent daily? (HH:MM format, default: $DEFAULT_TIME): " SEND_TIME
SEND_TIME=${SEND_TIME:-$DEFAULT_TIME}

# Parse time
IFS=':' read -ra TIME_PARTS <<< "$SEND_TIME"
HOUR=${TIME_PARTS[0]}
MINUTE=${TIME_PARTS[1]}

# Validate time format
if ! [[ "$HOUR" =~ ^[0-9]+$ ]] || ! [[ "$MINUTE" =~ ^[0-9]+$ ]] || [ "$HOUR" -gt 23 ] || [ "$MINUTE" -gt 59 ]; then
    echo "Error: Invalid time format. Please use HH:MM (24-hour format)"
    exit 1
fi

# Create cron entry
CRON_ENTRY="$MINUTE $HOUR * * * cd $SCRIPT_DIR && $UV_PATH run python run.py run >> $SCRIPT_DIR/logs/cron.log 2>&1"

echo "Cron entry will be:"
echo "$CRON_ENTRY"
echo ""

read -p "Add this cron job? (y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Cancelled."
    exit 0
fi

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✓ Cron job added successfully!"
echo "The newsletter will be sent daily at $SEND_TIME"
echo "Logs will be saved to: $SCRIPT_DIR/logs/cron.log"
echo ""
echo "To view your cron jobs: crontab -l"
echo "To remove this job: crontab -e (then delete the line)"