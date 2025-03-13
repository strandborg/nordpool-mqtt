#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Copy .env.example to .env if .env doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Done! Please edit the .env file with your MQTT broker details."
fi

# Copy docker-compose.override.yml.example to docker-compose.override.yml if it doesn't exist
if [ ! -f docker-compose.override.yml ]; then
    echo "Creating docker-compose.override.yml from template..."
    cp docker-compose.override.yml.example docker-compose.override.yml
    echo "Done! You can customize docker-compose.override.yml for your development environment."
fi

echo "Setup complete. You can now run 'docker-compose up -d' to start the application." 