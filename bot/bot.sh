#!/bin/bash
# Sigmond_Tarot Bot Manager - Start/Stop Sigmond_Tarot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="sigmond_tarot.pid"
LOG_FILE="sigmond_tarot.log"
SIGMOND_TAROT_SCRIPT="$SCRIPT_DIR/sigmond_tarot_steps.py"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if Sigmond_Tarot is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is dead
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Start Sigmond_Tarot
start_sigmond_tarot() {
    if is_running; then
        echo -e "${YELLOW}Sigmond_Tarot is already running with PID: $(cat "$PID_FILE")${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Starting Sigmond_Tarot ...${NC}"
    
    # Check if wiki.py exists
    if [ ! -f "$SIGMOND_TAROT_SCRIPT" ]; then
        echo -e "${RED}Error: $SIGMOND_TAROT_SCRIPT not found!${NC}"
        return 1
    fi
    
    # Start Sigmond_Tarot in background and redirect output to log file
    nohup python3 "$SIGMOND_TAROT_SCRIPT" --port 3009 > "$LOG_FILE" 2>&1 &
    PID=$!
    
    # Save PID to file
    echo $PID > "$PID_FILE"
    
    # Wait a moment to check if it started successfully
    sleep 2
    
    if is_running; then
        echo -e "${GREEN}✅ Sigmond_Tarot started successfully!${NC}"
        echo -e "   PID: $PID"
        echo -e "   Log: $LOG_FILE"
        echo -e "   URL: http://localhost:3000/sigmond_tarot"
        
        # Try to extract auth credentials from log
        if [ -f "$LOG_FILE" ]; then
            AUTH=$(grep "Basic Auth:" "$LOG_FILE" | tail -1)
            if [ ! -z "$AUTH" ]; then
                echo -e "   $AUTH"
            fi
        fi
    else
        echo -e "${RED}❌ Failed to start Sigmond_Tarot${NC}"
        echo -e "   Check $LOG_FILE for errors"
        return 1
    fi
}

# Stop Sigmond_Tarot
stop_sigmond_tarot() {
    if ! is_running; then
        echo -e "${YELLOW}Sigmond_Tarot is not running${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo -e "${GREEN}Stopping Sigmond_Tarot (PID: $PID)...${NC}"
    
    # Send SIGTERM for graceful shutdown
    kill -TERM "$PID" 2>/dev/null
    
    # Wait up to 5 seconds for process to stop
    for i in {1..5}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # If still running, force kill
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Sigmond_Tarot didn't stop gracefully, forcing shutdown...${NC}"
        kill -9 "$PID" 2>/dev/null
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    echo -e "${GREEN}✅ Sigmond_Tarot has been stopped${NC}"
}

# Check Sigmond_Tarot's status
status_sigmond_tarot() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}● Sigmond_Tarot is running${NC}"
        echo -e "   PID: $PID"
        echo -e "   URL: http://localhost:3000/sigmond_tarot"
        
        # Show process info
        ps -p "$PID" -o pid,vsz,rss,comm
        
        # Show last few log lines
        if [ -f "$LOG_FILE" ]; then
            echo -e "\n${YELLOW}Recent log entries:${NC}"
            tail -5 "$LOG_FILE"
        fi
    else
        echo -e "${RED}● Sigmond_Tarot is not running${NC}"
    fi
}

# Show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Sigmond_Tarot's logs (press Ctrl+C to exit):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}No log file found${NC}"
    fi
}

# Main script logic
case "$1" in
    start)
        start_sigmond_tarot
        ;;
    stop)
        stop_sigmond_tarot
        ;;
    restart)
        stop_sigmond_tarot
        sleep 1
        start_sigmond_tarot
        ;;
    status)
        status_sigmond_tarot
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "🤖 Sigmond_Tarot Bot Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start Sigmond_Tarot in the background"
        echo "  stop     - Stop Sigmond_Tarot gracefully"
        echo "  restart  - Restart Sigmond_Tarot"
        echo "  status   - Check if Sigmond_Tarot is running"
        echo "  logs     - Follow Sigmond_Tarot's logs"
        echo ""
        echo "Example:"
        echo "  $0 start   # Start Sigmond_Tarot"
        echo "  $0 status  # Check status"
        echo "  $0 stop    # Stop Sigmond_Tarot"
        ;;
esac
