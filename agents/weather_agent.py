import httpx
from typing import List, Dict
import os
import logging
from datetime import datetime, date
from ..schemas.inputs import TravelInput
from ..schemas.responses import WeatherInfo, LocalEvent, WeatherResponse
import asyncio
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

class WeatherAgent:
    def __init__(self):
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
        self.ticketmaster_api_key = os.getenv("TICKETMASTER_API_KEY")
        
        if not self.weather_api_key:
            raise ValueError("WEATHER_API_KEY environment variable is not set")
        if not self.ticketmaster_api_key:
            raise ValueError("TICKETMASTER_API_KEY environment variable is not set")
        
        self.weather_base_url = "http://api.weatherapi.com/v1"
        self.ticketmaster_base_url = "https://app.ticketmaster.com/discovery/v2"
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    async def _retry_with_exponential_backoff(self, func, *args, **kwargs):
        """Execute a function with exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = (2 ** attempt) * self.retry_delay
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    def _format_location(self, location: str) -> str:
        """Format location string for API requests."""
        try:
            # Remove special characters except spaces, hyphens, and basic punctuation
            formatted = re.sub(r'[^\w\s\-\.,]', '', location)
            # Normalize spaces
            formatted = ' '.join(formatted.split())
            # URL encode the location
            formatted = quote(formatted)
            logger.debug(f"Formatted location '{location}' to '{formatted}'")
            return formatted
        except Exception as e:
            logger.error(f"Error formatting location '{location}': {str(e)}")
            # Return a basic URL-encoded version as fallback
            return quote(location)

    async def get_weather_and_events(self, travel_input: TravelInput) -> WeatherResponse:
        try:
            # Convert string dates to date objects
            start_date = datetime.strptime(travel_input.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(travel_input.return_date, "%Y-%m-%d").date()
            
            # Get weather forecast
            weather_forecast = await self._fetch_weather_forecast(
                travel_input.destination,
                start_date,
                end_date
            )
            
            # Get local events
            local_events = await self._fetch_local_events(
                travel_input.destination,
                start_date,
                end_date
            )
            
            # Ensure we return empty lists instead of None
            return WeatherResponse(
                weather_forecast=weather_forecast or [],
                local_events=local_events or []
            )
        
        except Exception as e:
            logger.error(f"Error in WeatherAgent: {str(e)}")
            # Return empty lists on error
            return WeatherResponse(
                weather_forecast=[],
                local_events=[]
            )

    async def _fetch_weather_forecast(
        self,
        location: str,
        start_date: date,
        end_date: date
    ) -> List[WeatherInfo]:
        """Fetch weather forecast for the specified location and date range."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            days = (end_date - start_date).days + 1
            formatted_location = self._format_location(location)
            
            url = f"{self.weather_base_url}/forecast.json"
            params = {
                "key": self.weather_api_key,
                "q": formatted_location,
                "days": min(days, 14),  # API limit is 14 days
                "aqi": "no"
            }
            
            try:
                logger.info(f"Fetching weather forecast for {location} for {days} days")
                response = await self._retry_with_exponential_backoff(
                    client.get,
                    url,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                forecast_days = []
                
                if "forecast" in data and "forecastday" in data["forecast"]:
                    for day in data["forecast"]["forecastday"]:
                        try:
                            forecast_days.append(
                                WeatherInfo(
                                    date=day["date"],
                                    temperature_celsius=str(day["day"]["avgtemp_c"]),
                                    condition=day["day"]["condition"]["text"],
                                    precipitation_chance=str(day["day"]["daily_chance_of_rain"]),
                                    humidity=str(day["day"]["avghumidity"])
                                )
                            )
                        except (KeyError, ValueError) as e:
                            logger.warning(f"Error processing weather day data: {str(e)}")
                            continue
                
                if not forecast_days:
                    logger.warning(f"No weather data found for {location}")
                else:
                    logger.info(f"Successfully fetched {len(forecast_days)} days of weather data")
                
                return forecast_days
            
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching weather forecast: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Error fetching weather forecast: {str(e)}")
                return []

    async def _fetch_local_events(
        self,
        location: str,
        start_date: date,
        end_date: date
    ) -> List[LocalEvent]:
        async with httpx.AsyncClient() as client:
            url = f"{self.ticketmaster_base_url}/events.json"
            
            # Convert dates to datetime with time
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            params = {
                "apikey": self.ticketmaster_api_key,
                "city": location,
                "startDateTime": start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endDateTime": end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "size": 20  # Limit number of events
            }
            
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                events = []
                
                if "_embedded" in data and "events" in data["_embedded"]:
                    for event in data["_embedded"]["events"]:
                        try:
                            # Extract price range if available
                            price_range = "N/A"
                            if "priceRanges" in event:
                                min_price = event["priceRanges"][0].get("min", 0)
                                max_price = event["priceRanges"][0].get("max", 0)
                                if min_price or max_price:
                                    price_range = f"${min_price}-${max_price}"
                            
                            # Extract venue name
                            venue_name = "Unknown Venue"
                            if "_embedded" in event and "venues" in event["_embedded"]:
                                venue_name = event["_embedded"]["venues"][0].get("name", "Unknown Venue")
                            
                            # Extract category
                            category = "Other"
                            if "classifications" in event and event["classifications"]:
                                segment = event["classifications"][0].get("segment", {})
                                category = segment.get("name", "Other")
                            
                            # Extract and parse datetime
                            event_datetime = datetime.now()
                            if "dates" in event and "start" in event["dates"]:
                                datetime_str = event["dates"]["start"].get("dateTime")
                                if datetime_str:
                                    # Handle both Z and +00:00 timezone formats
                                    datetime_str = datetime_str.replace("Z", "+00:00")
                                    event_datetime = datetime.fromisoformat(datetime_str)
                            
                            events.append(
                                LocalEvent(
                                    name=event.get("name", "Unnamed Event"),
                                    date=event_datetime.strftime("%Y-%m-%d"),
                                    venue=venue_name,
                                    category=category,
                                    price_range=price_range,
                                    description=event.get("description", "No description available")
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Error processing event {event.get('name', 'unknown')}: {str(e)}")
                            continue
                
                return events
            
            except httpx.HTTPError as e:
                logger.error(f"Error fetching local events: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Error fetching local events: {str(e)}")
                return [] 