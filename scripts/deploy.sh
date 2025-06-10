#!/bin/bash
# SolarScope Pro - Docker Deployment Script

set -e

echo "🐳 SolarScope Pro - Docker Deployment"
echo "====================================="

# Configuration
PROJECT_NAME="solarscope-pro"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE="config/.env.production"

# Functions
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  dev        Start development environment"
    echo "  prod       Start production environment"
    echo "  stop       Stop all services"
    echo "  restart    Restart all services"
    echo "  logs       Show logs"
    echo "  build      Build images"
    echo "  clean      Clean up containers and volumes"
    echo "  status     Show service status"
    echo ""
    echo "Options:"
    echo "  --rebuild  Force rebuild of images"
    echo "  --follow   Follow logs output"
}

check_requirements() {
    echo "🔍 Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed!"
        exit 1
    fi
    
    echo "✅ Docker and Docker Compose are available"
}

setup_environment() {
    echo "🔧 Setting up environment..."
    
    # Create logs directory
    mkdir -p logs
    
    # Copy environment file if it doesn't exist
    if [ ! -f "config/.env" ]; then
        if [ -f "$ENV_FILE" ]; then
            cp "$ENV_FILE" "config/.env"
            echo "📝 Copied production environment template"
            echo "⚠️  Please edit config/.env with your settings!"
        else
            echo "❌ No environment file found!"
            exit 1
        fi
    fi
    
    echo "✅ Environment setup complete"
}

dev_start() {
    echo "🚀 Starting development environment..."
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
    echo "✅ Development environment started"
    echo "📍 API: http://localhost:8000"
    echo "📚 Docs: http://localhost:8000/docs"
    echo "🗄️  Database: localhost:5432"
}

prod_start() {
    echo "🚀 Starting production environment..."
    docker-compose --profile production up -d
    echo "✅ Production environment started"
    echo "📍 API: http://localhost:80"
    echo "📚 Docs: http://localhost:80/docs"
    echo "🔒 Nginx: http://localhost:80"
}

stop_services() {
    echo "🛑 Stopping all services..."
    docker-compose down
    echo "✅ All services stopped"
}

restart_services() {
    echo "🔄 Restarting services..."
    stop_services
    sleep 2
    if [ "$ENVIRONMENT" = "prod" ]; then
        prod_start
    else
        dev_start
    fi
}

show_logs() {
    if [ "$FOLLOW_LOGS" = "true" ]; then
        echo "📋 Following logs (Ctrl+C to exit)..."
        docker-compose logs -f
    else
        echo "📋 Recent logs:"
        docker-compose logs --tail=50
    fi
}

build_images() {
    echo "🔨 Building images..."
    if [ "$REBUILD" = "true" ]; then
        docker-compose build --no-cache
    else
        docker-compose build
    fi
    echo "✅ Images built successfully"
}

clean_up() {
    echo "🧹 Cleaning up..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    echo "✅ Cleanup complete"
}

show_status() {
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "🔍 Health Checks:"
    docker-compose exec solarscope-api curl -f http://localhost:8000/api/v1/health 2>/dev/null | python -m json.tool || echo "API not responding"
}

# Parse arguments
COMMAND=""
REBUILD="false"
FOLLOW_LOGS="false"
ENVIRONMENT="dev"

while [[ $# -gt 0 ]]; do
    case $1 in
        dev|prod|stop|restart|logs|build|clean|status)
            COMMAND="$1"
            if [ "$1" = "prod" ]; then
                ENVIRONMENT="prod"
            fi
            shift
            ;;
        --rebuild)
            REBUILD="true"
            shift
            ;;
        --follow)
            FOLLOW_LOGS="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
check_requirements
setup_environment

case "$COMMAND" in
    dev)
        dev_start
        ;;
    prod)
        prod_start
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    build)
        build_images
        ;;
    clean)
        clean_up
        ;;
    status)
        show_status
        ;;
    "")
        echo "No command specified."
        show_help
        exit 1
        ;;
    *)
        echo "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
