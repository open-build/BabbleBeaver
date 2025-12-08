#!/bin/bash

# BabbleBeaver Startup Script
# Manages local development environment setup and service lifecycle

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"
PID_FILE="ops/babblebeaver.pid"
LOG_FILE="ops/babblebeaver.log"
APP_MODULE="main:app"
DEFAULT_PORT=8004

# Helper functions
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  BabbleBeaver Local Development Manager${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_warning "Virtual environment not found at $VENV_DIR"
        return 1
    fi
    return 0
}

# Create virtual environment
create_venv() {
    print_info "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
    else
        print_error "Could not find activation script"
        exit 1
    fi
}

# Check if requirements are installed/up-to-date
check_requirements() {
    print_info "Checking Python dependencies..."
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Check if pip freeze matches requirements
    if pip freeze | grep -q -F -f "$REQUIREMENTS_FILE" 2>/dev/null; then
        print_success "Dependencies are up to date"
        return 0
    else
        print_warning "Dependencies need to be installed/updated"
        return 1
    fi
}

# Install/update requirements
install_requirements() {
    print_info "Installing/updating Python dependencies..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    print_success "Dependencies installed successfully"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found"
        
        if [ -f "example.env" ]; then
            print_info "Would you like to create .env from example.env? (y/n)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                cp example.env .env
                print_success ".env created from example.env"
                print_warning "Please edit .env and add your configuration"
                print_info "Run: python setup_admin.py for guided setup"
                exit 0
            else
                print_error ".env file is required. Please create it manually."
                exit 1
            fi
        else
            print_error ".env file is required. Please create it manually."
            exit 1
        fi
    else
        print_success ".env file found"
    fi
}

# Check if database needs migration
check_database() {
    if [ -f "chatbot.db" ]; then
        print_info "Database found - checking if migration is needed..."
        
        # Check if migrate script exists
        if [ -f "migrate_db.py" ]; then
            print_info "Run database migration? (y/n)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                python migrate_db.py
            fi
        fi
    else
        print_info "No existing database - will be created on first run"
    fi
}

# Get process ID from PID file
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# Check if service is running
is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Start the service
start_service() {
    print_info "Starting BabbleBeaver service..."
    
    if is_running; then
        print_warning "Service is already running (PID: $(get_pid))"
        return 0
    fi
    
    # Create ops directory if it doesn't exist
    mkdir -p ops
    
    # Start uvicorn in background
    nohup uvicorn "$APP_MODULE" \
        --host 0.0.0.0 \
        --port "$DEFAULT_PORT" \
        --reload \
        > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment and check if it's still running
    sleep 2
    if is_running; then
        print_success "Service started successfully (PID: $pid)"
        print_info "Access the application at: http://localhost:$DEFAULT_PORT"
        print_info "Admin dashboard at: http://localhost:$DEFAULT_PORT/admin/login-page"
        print_info "Logs: tail -f $LOG_FILE"
        return 0
    else
        print_error "Service failed to start. Check logs: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Stop the service
stop_service() {
    print_info "Stopping BabbleBeaver service..."
    
    local pid=$(get_pid)
    
    if [ -z "$pid" ]; then
        print_warning "PID file not found"
    elif ! ps -p "$pid" > /dev/null 2>&1; then
        print_warning "Process not running (stale PID file)"
        rm -f "$PID_FILE"
    else
        print_info "Sending TERM signal to process $pid..."
        kill "$pid"
        
        # Wait for process to terminate
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Process did not terminate gracefully, forcing..."
            kill -9 "$pid"
        fi
        
        rm -f "$PID_FILE"
        print_success "Service stopped successfully"
    fi
}

# Restart the service
restart_service() {
    print_info "Restarting BabbleBeaver service..."
    stop_service
    sleep 1
    start_service
}

# Show service status
show_status() {
    print_header
    echo ""
    
    if is_running; then
        local pid=$(get_pid)
        print_success "Service is RUNNING (PID: $pid)"
        echo ""
        print_info "Process details:"
        ps -p "$pid" -o pid,ppid,user,%cpu,%mem,etime,command
    else
        print_warning "Service is NOT RUNNING"
    fi
    
    echo ""
    print_info "Service URLs:"
    echo "  Main application: http://localhost:$DEFAULT_PORT"
    echo "  Admin dashboard:  http://localhost:$DEFAULT_PORT/admin/login-page"
    echo "  API docs:         http://localhost:$DEFAULT_PORT/docs"
    
    echo ""
    print_info "Log file: $LOG_FILE"
    
    if [ -f "$LOG_FILE" ]; then
        echo ""
        print_info "Recent logs (last 10 lines):"
        tail -n 10 "$LOG_FILE"
    fi
}

# Setup the environment
setup_environment() {
    print_header
    echo ""
    
    # Check/create virtual environment
    if ! check_venv; then
        create_venv
    else
        print_success "Virtual environment found"
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Check/install requirements
    if ! check_requirements; then
        install_requirements
    fi
    
    # Check .env file
    check_env_file
    
    # Check database
    check_database
    
    echo ""
    print_success "Environment setup complete!"
}

# Show help
show_help() {
    print_header
    echo ""
    echo "Usage: $0 {start|stop|restart|status|setup|logs|help}"
    echo ""
    echo "Commands:"
    echo "  start     - Start the BabbleBeaver service"
    echo "  stop      - Stop the BabbleBeaver service"
    echo "  restart   - Restart the BabbleBeaver service"
    echo "  status    - Show service status and recent logs"
    echo "  setup     - Setup/update virtual environment and dependencies"
    echo "  logs      - Follow the application logs"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup         # First time setup"
    echo "  $0 start         # Start the service"
    echo "  $0 restart       # Restart the service"
    echo "  $0 logs          # Watch the logs"
    echo ""
}

# Follow logs
follow_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "Following logs (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
    else
        print_error "Log file not found: $LOG_FILE"
        exit 1
    fi
}

# Main command handler
main() {
    case "${1:-help}" in
        setup)
            setup_environment
            ;;
        start)
            setup_environment
            echo ""
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            setup_environment
            echo ""
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            follow_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
