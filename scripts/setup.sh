#!/bin/bash

# ML Drift Detection System - Setup Script
# This script sets up and starts the entire system

set -e

echo "=========================================="
echo "ML Drift Detection System - Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose is installed${NC}"
echo ""

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/raw data/processed data/models
mkdir -p backend/models
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Database Configuration
POSTGRES_USER=mluser
POSTGRES_PASSWORD=mlpassword
POSTGRES_DB=ml_monitoring
DATABASE_URL=postgresql://mluser:mlpassword@postgres:5432/ml_monitoring

# Backend Configuration
MODEL_PATH=./models
LOG_LEVEL=INFO

# Monitoring Configuration
MONITORING_INTERVAL=30
DRIFT_WINDOW_HOURS=1
PSI_THRESHOLD=0.25
KS_THRESHOLD=0.05

# Traffic Simulator
BACKEND_URL=http://backend:8000
DEFAULT_RPS=10

# Frontend Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo -e "${YELLOW}⚠ .env file already exists, skipping${NC}"
fi
echo ""

# Build Docker images
echo "Building Docker images..."
echo "This may take a few minutes on first run..."
docker-compose build
echo -e "${GREEN}✓ Docker images built${NC}"
echo ""

# Start database first and wait for it to be ready
echo "Starting database..."
docker-compose up -d postgres
echo "Waiting for database to be ready..."
sleep 10
echo -e "${GREEN}✓ Database started${NC}"
echo ""

# Train the ML model
echo "=========================================="
echo "Training ML Model"
echo "=========================================="
echo "This will generate synthetic data and train the model..."
docker-compose run --rm backend python -m app.ml.train
echo -e "${GREEN}✓ Model trained successfully${NC}"
echo ""

# Start all services
echo "=========================================="
echo "Starting All Services"
echo "=========================================="
docker-compose up -d
echo ""

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 15
echo ""

# Check service health
echo "=========================================="
echo "Service Status"
echo "=========================================="
echo ""

# Check backend health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend API is running${NC}"
else
    echo -e "${RED}✗ Backend API is not responding${NC}"
fi

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend is still starting...${NC}"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "🎯 Access Points:"
echo "   Frontend Dashboard: http://localhost:3000"
echo "   Backend API:        http://localhost:8000"
echo "   API Documentation:  http://localhost:8000/docs"
echo ""
echo "📊 The system is now:"
echo "   - Generating synthetic transactions"
echo "   - Making predictions"
echo "   - Monitoring for drift"
echo "   - Updating the dashboard in real-time"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:          docker-compose logs -f"
echo "   Stop system:        docker-compose down"
echo "   Restart system:     docker-compose restart"
echo "   View status:        docker-compose ps"
echo ""
echo "🔍 To see the system in action:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Watch the Overview tab for live predictions"
echo "   3. Check the Drift Detection tab for feature drift"
echo "   4. Monitor Performance tab for metrics over time"
echo ""
echo "Happy monitoring! 🚀"
echo ""

