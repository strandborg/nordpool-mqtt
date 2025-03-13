# Check if Python is installed
try {
    python --version
}
catch {
    Write-Error "Python is not installed or not in the PATH. Please install Python 3.8 or newer."
    exit 1
}

# Create a virtual environment
Write-Host "Creating a Python virtual environment..."
python -m venv venv

# Activate the virtual environment
Write-Host "Activating virtual environment..."
. .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..."
pip install -r requirements.txt

# Set up .env file if it doesn't exist
if (-not (Test-Path -Path ".env")) {
    Write-Host "Creating .env file from template..."
    Copy-Item ".env.example" ".env"
    Write-Host "Done! Please edit the .env file with your MQTT broker details."
}

Write-Host "Virtual environment setup complete."
Write-Host "To activate the environment in the future, run: . .\venv\Scripts\Activate.ps1"
Write-Host "To run the application, run: python app\main.py" 