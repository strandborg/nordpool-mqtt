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
import pytz
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from nordpool import elspot
from apscheduler.schedulers.background import BackgroundScheduler
from homie.device_base import Device_Base
from homie.node.node_base import Node_Base
from homie.node.property.property_float import Property_Float

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("nordpool_price_tracker")

# Load environment variables
load_dotenv()

# MQTT configuration
NORDPOOL_REGION = os.getenv("NORDPOOL_REGION", "FI")
device_id = os.environ.get("MQTT_DEVICE_ID", "nordpool-price")
device_name = os.environ.get("MQTT_DEVICE_NAME", "Nordpool Price")

mqtt_settings = {
    'MQTT_BROKER' : os.environ.get("MQTT_BROKER", "localhost"),
    'MQTT_PORT' : int(os.environ.get("MQTT_BROKER_PORT", 1883)),
    'MQTT_USERNAME' : os.environ.get("MQTT_USERNAME", None),
    'MQTT_PASSWORD' : os.environ.get("MQTT_PASSWORD", None)
}

class NordpoolPrice(Device_Base):
    """Tracks Nordpool electricity prices and publishes updates to MQTT."""
    def __init__(self, device_id=None, name=None, homie_settings=None, mqtt_settings=None):
        super().__init__(device_id, name, homie_settings, mqtt_settings)

        self.prices: Dict[datetime.datetime, float] = {}
        self.current_price: Optional[float] = 0.0
        self.spot_api = elspot.Prices()
        self.scheduler = BackgroundScheduler()
                
        node = Node_Base(self, "price", "Price", "electricity")
        self.node = node
        self.add_node(node)

        self.price_property = Property_Float(self.node, id="currentprice", name="Current Price", unit="c/kWh", settable=False)
        self.node.add_property(self.price_property)
        self.start()
        
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

            self.price_property.value = payload

        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
    
    def fetch_prices(self):
        """Fetch prices from Nordpool API."""
        try:
            logger.info("Fetching prices from Nordpool")
            
            
            # Get today's and tomorrow's dates in the region's timezone
            today = datetime.datetime.now(pytz.UTC).date()
            tomorrow = today + datetime.timedelta(days=1)
            
            logger.info(f"Fetching prices for {NORDPOOL_REGION} region, today: {today}, tomorrow: {tomorrow}")
            
            # Fetch prices for the specified region
            today_prices = self.spot_api.hourly(areas=[NORDPOOL_REGION], end_date=today)
            tomorrow_prices = self.spot_api.hourly(areas=[NORDPOOL_REGION], end_date=tomorrow)
            
            # Clear existing prices before adding new ones
            self.prices.clear()
            
            # Process and store prices
            self._process_prices(today_prices)
            self._process_prices(tomorrow_prices)
            
            logger.info(f"Successfully fetched {len(self.prices)} prices")
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
    
    def _process_prices(self, price_data):
        """Process price data from Nordpool API."""
        if not price_data or "areas" not in price_data or NORDPOOL_REGION not in price_data["areas"]:
            logger.warning(f"No price data available for {NORDPOOL_REGION} area")
            return
        
        for hour_data in price_data["areas"][NORDPOOL_REGION]["values"]:
            # The start time from Nordpool already has timezone info
            # We need to remove it to match our datetime objects without timezone
            start_time = hour_data["start"].astimezone(pytz.UTC)
            price = hour_data["value"]
            self.prices[start_time] = price
    
    def check_current_price(self):
        """Check and update the current active price."""
        if not self.prices:
            logger.warning("No price data available")
            return
        
        # Get current time in the region's timezone instead of system time
        utc_now = datetime.datetime.now(pytz.UTC)
        
        # Replace timezone info to match the format in self.prices
        now = utc_now.replace(minute=0, second=0, microsecond=0)
        
        logger.info(f"Checking price for time: {now}")
        
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
                
        super().start()
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
#    try:
    # Check if all required environment variables are set
    if not mqtt_settings['MQTT_BROKER']:
        logger.error("MQTT_BROKER environment variable is not set")
        return
    
    logger.info("Starting Nordpool Price Tracker application")
    
    # Create and start tracker
    tracker = NordpoolPrice(name=device_name, device_id=device_id, mqtt_settings=mqtt_settings)
    
    # Keep the program running
    while True:
        time.sleep(60)
            
#    except KeyboardInterrupt:
#        logger.info("Application stopped by user")
#    except Exception as e:
#        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main() 