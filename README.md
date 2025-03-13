# Nordpool MQTT Price Tracker

A Dockerized Python application that fetches electricity spot prices from Nordpool for the Finland region and publishes price updates to MQTT.

## Features

- Fetches Nordpool spot prices once a day for the Finland (FI) region
- Monitors price changes (which occur every 15 minutes)
- Publishes current active price to an MQTT topic whenever the price changes
- Configurable MQTT settings through environment variables
- Dockerized for easy deployment

## Setup

### Prerequisites

- Docker and Docker Compose
- Git (for cloning the repository)

### Configuration

Create a `.env` file in the project root with the following variables:

```
MQTT_BROKER=mqtt.example.com
MQTT_PORT=1883
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password
MQTT_TOPIC=electricity/nordpool/price
MQTT_CLIENT_ID=nordpool-price-tracker
```

### Running with Docker

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

## Development

### Local Development Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create and configure `.env` file (see Configuration section)

4. Run the application:
   ```bash
   python app/main.py
   ```

## License

MIT 