#!/bin/bash

# Server setup script - run once on your server

# Install Docker and Docker Compose if not installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create project directory
mkdir -p /home/$USER/relivchats-api
cd /home/$USER/relivchats-api

# Create uploads directory
mkdir -p uploads

echo "✅ Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy docker-compose.yml to this directory"
echo "2. Set up GitHub Secrets (see README)"
echo "3. Push to 'production' branch to deploy"
echo ""
echo "After deployment:"
echo "- Access Nginx Proxy Manager at http://YOUR_SERVER_IP:81"
echo "- Default login: admin@example.com / changeme"
echo "- Access Flower (Celery monitoring) at http://YOUR_SERVER_IP:5555"