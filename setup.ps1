# Create logs directory if it doesn't exist
if (-not (Test-Path -Path "logs")) {
    Write-Host "Creating logs directory..."
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Copy .env.example to .env if .env doesn't exist
if (-not (Test-Path -Path ".env")) {
    Write-Host "Creating .env file from template..."
    Copy-Item ".env.example" ".env"
    Write-Host "Done! Please edit the .env file with your MQTT broker details."
}

# Copy docker-compose.override.yml.example to docker-compose.override.yml if it doesn't exist
if (-not (Test-Path -Path "docker-compose.override.yml")) {
    Write-Host "Creating docker-compose.override.yml from template..."
    Copy-Item "docker-compose.override.yml.example" "docker-compose.override.yml"
    Write-Host "Done! You can customize docker-compose.override.yml for your development environment."
}

Write-Host "Setup complete. You can now run 'docker-compose up -d' to start the application." 