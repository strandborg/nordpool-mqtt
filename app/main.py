#!/usr/bin/env python3
"""
Nordpool MQTT Price Tracker

Fetches electricity spot prices from Nordpool for FI region and
publishes the current active price to MQTT whenever it changes.
"""

import os
import time
import logging
import datetime
import pprint
from typing import Dict, List, Optional
from pathlib import Path
#from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from nordpool import elspot
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("nordpool_price_tracker")

# Load environment variables
#load_dotenv()

# MQTT configuration
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "electricity/nordpool/price")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "nordpool-price-tracker")


class NordpoolPriceTracker:
    """Tracks Nordpool electricity prices and publishes updates to MQTT."""

    def __init__(self):
        self.prices: Dict[datetime.datetime, float] = {}
        self.current_price: Optional[float] = None
        self.spot_api = elspot.Prices()
        self.scheduler = BackgroundScheduler()
        self.mqtt_client = self._setup_mqtt_client()
        
    def _setup_mqtt_client(self) -> mqtt.Client:
        """Set up and return MQTT client."""
        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        
        if MQTT_USERNAME and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            
        # Define MQTT callbacks
        client.on_connect = self._on_mqtt_connect
        client.on_disconnect = self._on_mqtt_disconnect
        
        return client
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        logger.warning(f"Disconnected from MQTT broker, return code: {rc}")
    
    def connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
    
    def _convert_price_to_cents_with_vat(self, price_eur_mwh: float) -> float:
        """
        Convert price from EUR/MWh to cents/kWh and add 25.5% VAT.
        
        Conversion:
        1 MWh = 1000 kWh
        1 EUR = 100 cents
        So EUR/MWh to cents/kWh: divide by 10
        Then add 25.5% VAT: multiply by 1.255
        """
        return (price_eur_mwh / 10) * 1.255
    
    def publish_price(self, price: float):
        """Publish price to MQTT topic."""
        try:
            # Convert price to cents/kWh with VAT before publishing
            converted_price = self._convert_price_to_cents_with_vat(price)
            payload = str(round(converted_price, 2))  # Round to 2 decimal places for readability
            result = self.mqtt_client.publish(MQTT_TOPIC, payload, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published price {converted_price:.3f} cents/kWh (with VAT) to {MQTT_TOPIC}")
            else:
                logger.error(f"Failed to publish price: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
    
    def fetch_prices(self):
        """Fetch prices from Nordpool API."""
        try:
            logger.info("Fetching prices from Nordpool")
            
            # Get today's and tomorrow's prices (to ensure we have the full day)
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            
            # Fetch prices for Finland area
            today_prices = self.spot_api.hourly(areas=["FI"])
            pprint.pprint(today_prices)
            tomorrow_prices = self.spot_api.hourly(areas=["FI"], end_date=tomorrow)
            
            # Process and store prices
            self._process_prices(today_prices)
            self._process_prices(tomorrow_prices)
            
            logger.info(f"Successfully fetched {len(self.prices)} prices")
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
    
    def _process_prices(self, price_data):
        """Process price data from Nordpool API."""
        if not price_data or "areas" not in price_data or "FI" not in price_data["areas"]:
            logger.warning("No price data available for FI area")
            return
        
        for hour_data in price_data["areas"]["FI"]["values"]:
            start_time = hour_data["start"].replace(tzinfo=None)
            price = hour_data["value"]
            self.prices[start_time] = price
    
    def check_current_price(self):
        """Check and update the current active price."""
        if not self.prices:
            logger.warning("No price data available")
            return
        
        # Get current time and find the active price period
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Check if we have data for the current hour
        if now in self.prices:
            new_price = self.prices[now]
            
            # Publish price if it's different from the current price
            if self.current_price != new_price:
                logger.info(f"Price changed: {self.current_price:.3f} -> {new_price:.3f} EUR/MWh")
                logger.info(f"Converted price: {self._convert_price_to_cents_with_vat(new_price):.3f} cents/kWh (with VAT)")
                self.current_price = new_price
                self.publish_price(new_price)
        else:
            logger.warning(f"No price data for current hour: {now}")
    
    def start(self):
        """Start the tracker."""
        logger.info("Starting Nordpool Price Tracker")
        
        # Connect to MQTT broker
        self.connect_mqtt()
        
        # Initial price fetch
        self.fetch_prices()
        self.check_current_price()
        
        # Schedule daily price fetching - fetch at 13:15 to ensure all data is available
        self.scheduler.add_job(
            self.fetch_prices, 
            trigger="cron", 
            hour=13, 
            minute=15, 
            id="fetch_prices"
        )
        
        # Schedule price check every 15 minutes
        self.scheduler.add_job(
            self.check_current_price, 
            trigger="cron", 
            minute="0,15,30,45", 
            id="check_price"
        )
        
        # Start the scheduler
        self.scheduler.start()
        
        logger.info("Tracker started successfully")


def main():
    """Main function to run the application."""
    try:
        # Check if all required environment variables are set
        if not MQTT_BROKER:
            logger.error("MQTT_BROKER environment variable is not set")
            return
        
        logger.info("Starting Nordpool Price Tracker application")
        
        # Create and start tracker
        tracker = NordpoolPriceTracker()
        tracker.start()
        
        # Keep the program running
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main() 