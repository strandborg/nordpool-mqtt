# Nordpool MQTT Price Tracker

A Dockerized Python application that fetches electricity spot prices from Nordpool for the a specific region and publishes price updates to MQTT using the Homie MQTT device definition, allowing automatic discovery of devices and properties by Home Assistant, OpenHAB, etc.

## Features

- Fetches Nordpool spot prices once a day for the a specific region
- Monitors price changes (which occur every 15 minutes)
- Publishes current active price to an MQTT topic whenever the price changes
- Configurable MQTT settings through environment variables
- Dockerized for easy deployment

## Setup

Fetch the Docker image from Docker Hub and run it directly:

```bash
docker pull strandborg/nordpool-price-tracker:latest
```


### Configuration

The following environment variables are required:

```
MQTT_BROKER=mqtt.example.com
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password

MQTT_PORT=<optional: MQTT server port, default: 1883)
NORDPOOL_REGION=<optional: Nordpool region code, default: FI>
MQTT_DEVICE_ID=<optional: Device ID, default: nordpool-price>
MQTT_DEVICE_NAME=<optional: Device Name, default: Nordpool Price>
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