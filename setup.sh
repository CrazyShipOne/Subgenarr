#!/bin/bash

# Subgenarr - Setup Script

set -e

echo "=========================================="
echo "Subgenarr - Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "IMPORTANT: Please edit .env file and configure:"
    echo "  - AUTH_USERNAME and AUTH_PASSWORD"
    echo "  - AI_BASE_URL, AI_API_KEY, and AI_MODEL"
    echo "  - TMDB_API_KEY and OMDB_API_KEY"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
else
    echo "✓ .env file already exists"
fi

# Create required directories
echo ""
echo "Creating required directories..."
mkdir -p config
mkdir -p media/movies
mkdir -p media/tv
mkdir -p tmp
echo "✓ Directories created"

# Build and start Docker images
echo ""
echo "Building Docker images (this may take a few minutes)..."
docker-compose build

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Place your media files in the ./media directory:"
echo "   - Movies: ./media/movies/"
echo "   - TV Shows: ./media/tv/"
echo ""
echo "2. Start the services:"
echo "   docker-compose up -d"
echo ""
echo "3. Access the web interface:"
echo "   http://localhost:3500"
echo ""
echo "4. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "For more information, see README.md"
echo ""
