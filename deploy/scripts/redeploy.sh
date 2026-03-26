#!/bin/bash

###############################################################################
# Backcast EVS - Redeployment Script
#
# This script automates the process of pulling latest changes, rebuilding
# containers, and running database migrations for the Backcast EVS application.
#
# Usage: ./scripts/redeploy.sh [options]
#
# Options:
#   -h, --help          Show this help message
#   -b, --branch        Specify git branch (default: current branch)
#   -s, --skip-backup   Skip database backup (NOT recommended)
#   -n, --no-build      Skip container rebuild (use existing images)
#   -m, --no-migrate    Skip database migrations
#   -y, --yes           Auto-confirm all prompts
#   -v, --verbose       Enable verbose output
#
# Examples:
#   ./scripts/redeploy.sh                    # Interactive redeployment
#   ./scripts/redeploy.sh -y                 # Non-interactive redeployment
#   ./scripts/redeploy.sh -b main            # Redeploy from main branch
#   ./scripts/redeploy.sh -s -n              # Skip backup and build (quick restart)
#
###############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
BRANCH=""
SKIP_BACKUP=false
SKIP_BUILD=false
SKIP_MIGRATE=false
AUTO_CONFIRM=false
VERBOSE=false

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$DEPLOY_DIR")"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           Backcast EVS - Redeployment Script                  ║"
    echo "║           Version 1.0 - Production Deployment                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    cat << EOF
Usage: $(basename "$0") [options]

Options:
    -h, --help          Show this help message
    -b, --branch BRANCH Specify git branch to pull from (default: current branch)
    -s, --skip-backup   Skip database backup (NOT recommended for production)
    -n, --no-build      Skip container rebuild (use existing images)
    -m, --no-migrate    Skip database migrations
    -y, --yes           Auto-confirm all prompts (non-interactive mode)
    -v, --verbose       Enable verbose output

Examples:
    $(basename "$0")                    # Interactive redeployment
    $(basename "$0") -y                 # Non-interactive redeployment
    $(basename "$0") -b main            # Redeploy from main branch
    $(basename "$0") -s -n              # Skip backup and build (quick restart)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -b|--branch)
                BRANCH="$2"
                shift 2
                ;;
            -s|--skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            -n|--no-build)
                SKIP_BUILD=true
                shift
                ;;
            -m|--no-migrate)
                SKIP_MIGRATE=true
                shift
                ;;
            -y|--yes)
                AUTO_CONFIRM=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# Confirm action if not in auto-confirm mode
confirm_action() {
    local message="$1"
    local default="${2:-n}"

    if [ "$AUTO_CONFIRM" = true ]; then
        return 0
    fi

    local prompt
    if [ "$default" = "y" ]; then
        prompt="$message [Y/n]: "
    else
        prompt="$message [y/N]: "
    fi

    while true; do
        read -p "$(echo -e ${YELLOW}$prompt${NC})" -n 1 -r response
        echo
        case $response in
            [Yy]|[Yy][Ee][Ss])
                return 0
                ;;
            [Nn]|[Nn][Oo]|"")
                if [ "$default" = "y" ] && [ -z "$response" ]; then
                    return 0
                fi
                return 1
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if we're in the correct directory
    if [ ! -f "$DEPLOY_DIR/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found in $DEPLOY_DIR"
        log_error "Please run this script from the correct location"
        exit 1
    fi

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
        log_error ".env.production not found in $DEPLOY_DIR"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Pull latest changes from git
pull_changes() {
    log_info "Pulling latest changes from git..."

    cd "$PROJECT_ROOT"

    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_verbose "Current branch: $current_branch"

    # If branch specified, switch to it
    if [ -n "$BRANCH" ]; then
        log_info "Switching to branch: $BRANCH"
        git checkout "$BRANCH"
    fi

    # Pull latest changes
    git pull origin "${BRANCH:-$current_branch}"

    log_success "Git pull completed"
}

# Backup database
backup_database() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "Skipping database backup (per user request)"
        return
    fi

    log_info "Creating database backup..."

    cd "$DEPLOY_DIR"

    # Create backup with timestamp
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql.gz"

    docker compose --env-file .env.production exec postgres \
        pg_dump -U backcast_prod backcast_evs | gzip > "$backup_file"

    if [ -f "$backup_file" ]; then
        local backup_size=$(du -h "$backup_file" | cut -f1)
        log_success "Database backup created: $backup_file ($backup_size)"
    else
        log_error "Failed to create database backup"
        exit 1
    fi
}

# Rebuild containers
rebuild_containers() {
    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping container rebuild (per user request)"
        return
    fi

    log_info "Rebuilding Docker containers..."
    log_verbose "This may take 5-15 minutes depending on your system"

    cd "$DEPLOY_DIR"

    if docker compose --env-file .env.production build; then
        log_success "Container build completed"
    else
        log_error "Container build failed"
        exit 1
    fi
}

# Restart services
restart_services() {
    log_info "Restarting services..."

    cd "$DEPLOY_DIR"

    if docker compose --env-file .env.production up -d; then
        log_success "Services restarted"
    else
        log_error "Failed to restart services"
        exit 1
    fi

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
}

# Run database migrations
run_migrations() {
    if [ "$SKIP_MIGRATE" = true ]; then
        log_warning "Skipping database migrations (per user request)"
        return
    fi

    log_info "Running database migrations..."

    cd "$DEPLOY_DIR"

    if docker compose --env-file .env.production run --rm alembic; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    cd "$DEPLOY_DIR"

    # Check service status
    log_verbose "Checking service status..."
    local status=$(docker compose --env-file .env.production ps --format json)

    # Count services
    local total_services=$(echo "$status" | jq '. | length')
    local running_services=$(echo "$status" | jq '[.[] | select(.State == "Running")] | length')

    log_verbose "Services: $running_services/$total_services running"

    # Check if backend is responding
    log_verbose "Checking backend health..."
    if curl -s -H "Host: api.backcast.duckdns.org" http://localhost:8080/docs > /dev/null; then
        log_success "Backend API is responding"
    else
        log_warning "Backend API might not be fully ready yet"
    fi

    # Check frontend
    log_verbose "Checking frontend..."
    if curl -s -H "Host: app.backcast.duckdns.org" http://localhost:8080/ > /dev/null; then
        log_success "Frontend is responding"
    else
        log_warning "Frontend might not be fully ready yet"
    fi

    # Check database migration version
    log_verbose "Checking database migration version..."
    local db_version=$(docker compose --env-file .env.production exec -T postgres \
        psql -U backcast_prod -d backcast_evs -t -c "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1;" 2>/dev/null | tr -d ' ')

    if [ -n "$db_version" ]; then
        log_success "Database migration version: $db_version"
    fi

    log_success "Deployment verification completed"
}

# Print summary
print_summary() {
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    Deployment Completed                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Service Status:"
    cd "$DEPLOY_DIR"
    docker compose --env-file .env.production ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | grep -v "NAMES"
    echo
    echo "Access URLs:"
    echo "  Frontend: http://app.backcast.duckdns.org:8080"
    echo "           https://app.backcast.duckdns.org"
    echo "  Backend:  http://api.backcast.duckdns.org:8080"
    echo "           https://api.backcast.duckdns.org"
    echo "  API Docs: https://api.backcast.duckdns.org/docs"
    echo
    echo "Management Commands:"
    echo "  View logs:    cd $DEPLOY_DIR && docker compose --env-file .env.production logs -f"
    echo "  Stop services: cd $DEPLOY_DIR && docker compose --env-file .env.production down"
    echo "  Restart:      cd $DEPLOY_DIR && docker compose --env-file .env.production restart"
    echo
}

# Main execution
main() {
    print_banner

    parse_args "$@"

    # Show configuration if verbose
    if [ "$VERBOSE" = true ]; then
        log_verbose "Configuration:"
        log_verbose "  Branch: ${BRANCH:-current}"
        log_verbose "  Skip backup: $SKIP_BACKUP"
        log_verbose "  Skip build: $SKIP_BUILD"
        log_verbose "  Skip migrations: $SKIP_MIGRATE"
        log_verbose "  Auto-confirm: $AUTO_CONFIRM"
        echo
    fi

    # Confirm before proceeding
    if ! confirm_action "Proceed with deployment?"; then
        log_warning "Deployment cancelled by user"
        exit 0
    fi

    # Execute deployment steps
    check_prerequisites
    pull_changes
    backup_database
    rebuild_containers
    restart_services
    run_migrations
    verify_deployment
    print_summary

    log_success "Redeployment completed successfully!"
}

# Run main function
main "$@"
