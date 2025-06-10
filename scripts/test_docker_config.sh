#!/bin/bash
# Test script to validate Docker configuration

echo "🧪 Testing Docker configuration..."

# Check if Dockerfile exists and is valid
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile found"
    
    # Check for common Dockerfile issues
    if grep -q "FROM python:3.11-slim" Dockerfile; then
        echo "✅ Valid base image"
    else
        echo "❌ Invalid or missing base image"
    fi
    
    if grep -q "WORKDIR /app" Dockerfile; then
        echo "✅ Working directory set"
    else
        echo "❌ Working directory not set"
    fi
    
    if grep -q "COPY requirements.txt" Dockerfile; then
        echo "✅ Requirements copied before app code (good caching)"
    else
        echo "⚠️  Requirements not copied separately"
    fi
    
    if grep -q "HEALTHCHECK" Dockerfile; then
        echo "✅ Health check configured"
    else
        echo "⚠️  No health check found"
    fi
else
    echo "❌ Dockerfile not found"
    exit 1
fi

# Check docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml found"
    
    # Check for required services
    if grep -q "timescaledb:" docker-compose.yml; then
        echo "✅ TimescaleDB service configured"
    else
        echo "❌ TimescaleDB service missing"
    fi
    
    if grep -q "solarscope-api:" docker-compose.yml; then
        echo "✅ API service configured"
    else
        echo "❌ API service missing"
    fi
    
    if grep -q "healthcheck:" docker-compose.yml; then
        echo "✅ Health checks configured"
    else
        echo "⚠️  No health checks in compose"
    fi
    
    if grep -q "networks:" docker-compose.yml; then
        echo "✅ Custom network configured"
    else
        echo "⚠️  Using default network"
    fi
else
    echo "❌ docker-compose.yml not found"
    exit 1
fi

# Check .dockerignore
if [ -f ".dockerignore" ]; then
    echo "✅ .dockerignore found"
    
    if grep -q "__pycache__" .dockerignore; then
        echo "✅ Python cache ignored"
    else
        echo "⚠️  Python cache not ignored"
    fi
    
    if grep -q "venv/" .dockerignore; then
        echo "✅ Virtual environment ignored"
    else
        echo "⚠️  Virtual environment not ignored"
    fi
else
    echo "⚠️  .dockerignore not found"
fi

# Check environment files
if [ -f "config/.env.production" ]; then
    echo "✅ Production environment template found"
else
    echo "⚠️  Production environment template missing"
fi

# Check deployment script
if [ -f "scripts/deploy.sh" ] && [ -x "scripts/deploy.sh" ]; then
    echo "✅ Deployment script found and executable"
else
    echo "⚠️  Deployment script missing or not executable"
fi

# Check requirements.txt
if [ -f "requirements.txt" ]; then
    echo "✅ Requirements file found"
    
    if grep -q "fastapi" requirements.txt; then
        echo "✅ FastAPI dependency found"
    else
        echo "❌ FastAPI dependency missing"
    fi
    
    if grep -q "uvicorn" requirements.txt; then
        echo "✅ Uvicorn dependency found"
    else
        echo "❌ Uvicorn dependency missing"
    fi
    
    if grep -q "gunicorn" requirements.txt; then
        echo "✅ Gunicorn for production found"
    else
        echo "⚠️  Gunicorn for production missing"
    fi
    
    if grep -q "asyncpg" requirements.txt; then
        echo "✅ AsyncPG database driver found"
    else
        echo "❌ AsyncPG database driver missing"
    fi
else
    echo "❌ requirements.txt not found"
    exit 1
fi

echo ""
echo "🎉 Docker configuration validation complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Install Docker and Docker Compose"
echo "  2. Copy config/.env.production to config/.env"
echo "  3. Edit config/.env with your settings"
echo "  4. Run: ./scripts/deploy.sh dev"
echo ""
echo "🔗 Useful commands:"
echo "  ./scripts/deploy.sh dev      # Start development environment"
echo "  ./scripts/deploy.sh prod     # Start production environment"
echo "  ./scripts/deploy.sh logs     # View logs"
echo "  ./scripts/deploy.sh status   # Check status"
