import google.generativeai as genai
from typing import List, Dict, Any
import os
import json
import logging
from datetime import datetime, timedelta
from schemas.inputs import TravelInput, UserPreferences
from schemas.responses import (
    WeatherInfo, LocalEvent, DailyItinerary,
    ItineraryResponse, WeatherResponse, RouteStop,
    Activity, Meal, Transport, Accommodation,
    WeatherSummary, EstimatedCosts, TripSummary
)
import re
import asyncio

logger = logging.getLogger(__name__)

class ItineraryGeneratorAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set")
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        logger.info("Initializing ItineraryGeneratorAgent with Gemini API")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.max_retries = 1
        self.retry_delay = 1  # seconds
        logger.info("ItineraryGeneratorAgent initialized successfully")

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

    async def generate_itinerary(
        self,
        travel_input: TravelInput,
        user_preferences: UserPreferences,
        weather_data: WeatherResponse
    ) -> ItineraryResponse:
        try:
            logger.info(f"Starting itinerary generation for destination: {travel_input.destination}")
            logger.info(f"Travel dates: {travel_input.start_date} to {travel_input.return_date}")
            logger.debug(f"User preferences: {user_preferences}")
            
            if not weather_data or not weather_data.weather_forecast:
                logger.error("No weather data available")
                raise ValueError("Weather data is required for itinerary generation")
            
            prompt = self._create_itinerary_prompt(
                travel_input,
                user_preferences,
                weather_data
            )
            logger.debug("Generated prompt for Gemini API")
            
            logger.info("Sending request to Gemini API with retries")
            response = await self._retry_with_exponential_backoff(
                self.model.generate_content_async,
                prompt
            )
            
            if not response or not response.text:
                logger.error("Empty response from Gemini API")
                raise ValueError("Failed to generate itinerary content")
                
            logger.info("Received response from Gemini API")
            
            logger.debug("Parsing itinerary response")
            result = self._parse_itinerary_response(response.text, weather_data)
            
            # Validate the result
            if not result or not result.daily_itineraries:
                logger.error("Invalid itinerary response structure")
                raise ValueError("Generated itinerary is invalid or empty")
            
            logger.info("Successfully generated itinerary")
            return result
        
        except ValueError as e:
            logger.error(f"Validation error in generate_itinerary: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_itinerary: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate itinerary: {str(e)}")

    def _create_itinerary_prompt(
        self,
        travel_input: TravelInput,
        user_preferences: UserPreferences,
        weather_data: WeatherResponse
    ) -> str:
        logger.info("Creating itinerary prompt")
        
        # Convert weather data to a more readable format
        logger.debug("Processing weather data")
        weather_info = []
        weather_conditions = set()
        for day in weather_data.weather_forecast:
            weather_info.append({
                "date": day.date,
                "temperature": day.temperature_celsius,
                "condition": day.condition,
                "precipitation_chance": day.precipitation_chance,
                "humidity": day.humidity
            })
            weather_conditions.add(day.condition.lower())
        logger.debug(f"Processed {len(weather_info)} days of weather data")
        
        # Generate weather-based activity suggestions
        activity_suggestions = self._generate_weather_based_suggestions(weather_conditions)
        
        # Convert events to a more readable format and sort by user preferences
        logger.debug("Processing and sorting events")
        events_info = []
        relevant_events = 0
        for event in weather_data.local_events:
            # Calculate event relevance score
            relevance_score = self._calculate_event_relevance(
                event,
                user_preferences.activities,
                weather_data.weather_forecast
            )
            if relevance_score > 1:
                relevant_events += 1

            events_info.append({
                "name": event.name,
                "date": event.date,
                "venue": event.venue,
                "category": event.category,
                "price_range": event.price_range,
                "relevance": relevance_score
            })
        
        events_info.sort(key=lambda x: x["relevance"], reverse=True)
        logger.info(f"Found {relevant_events} events matching user preferences out of {len(events_info)} total events")

        # Calculate budget information
        start_date = datetime.strptime(travel_input.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(travel_input.return_date, "%Y-%m-%d").date()
        days = (end_date - start_date).days + 1
        daily_budget = user_preferences.budget / days
        logger.info(f"Calculated daily budget: ${daily_budget:.2f} for {days} days")

        # Create the header section with dynamic destination information
        header = f"""As a travel itinerary expert, create a detailed day-by-day travel plan for a trip from {travel_input.origin} to {travel_input.destination} from {travel_input.start_date} to {travel_input.return_date}.

The destination {travel_input.destination} typically experiences {', '.join(weather_conditions)} during this period. Plan activities accordingly and include indoor alternatives where appropriate.\n\n"""

        # Create the preferences section with detailed budget breakdown
        transport_prefs = ', '.join(user_preferences.transport_preferences) if user_preferences.transport_preferences else 'Any'
        accommodation = user_preferences.accommodation_type if user_preferences.accommodation_type else 'Any'
        
        preferences = f"""User Preferences:
- Daily Budget: ${daily_budget:.2f} (Total: ${user_preferences.budget})
  * Suggested split: 
    - Activities: 40% (${daily_budget * 0.4:.2f})
    - Meals: 30% (${daily_budget * 0.3:.2f})
    - Transport: 20% (${daily_budget * 0.2:.2f})
    - Contingency: 10% (${daily_budget * 0.1:.2f})
- Preferred Activities: {', '.join(user_preferences.activities)}
- Meal Preferences: {', '.join(user_preferences.meal_preferences)}
- Must-Visit Places: {', '.join(user_preferences.preferred_places)}
- Transport Preferences: {transport_prefs}
- Accommodation Type: {accommodation}

Weather-Based Activity Suggestions:
{activity_suggestions}\n\n"""

        # Create the weather and events section with specific recommendations
        data_section = f"""Daily Weather Forecast:
{json.dumps(weather_info, indent=2)}

Local Events (Sorted by Relevance to User Preferences):
{json.dumps(events_info[:5], indent=2)}  # Show top 5 most relevant events

Event Integration Guidelines:
- Prioritize events with relevance score > 1.5
- Consider weather conditions when scheduling outdoor events
- Ensure event timing aligns with daily schedule
- Account for transport time to/from events\n\n"""

        # Create the instructions section with practical considerations
        instructions = """Please create a detailed itinerary that includes:
1. Trip Summary:
   - Overview of the complete journey
   - Daily highlights and main attractions
   - Budget allocation strategy
   - Weather contingency plans

2. Daily Itineraries:
   - Weather-appropriate activities
   - Meal recommendations matching preferences
   - Transport logistics between locations
   - Accommodation details with area benefits
   - Backup plans for weather-sensitive activities
   - Weather summary for the day
   - Local events happening that day
   - Daily route with coordinates

3. Practical Considerations:
   - Indoor alternatives for bad weather
   - Rest periods between activities
   - Transport connection times
   - Meal timing with activities
   - Local customs and etiquette

4. Cost Management:
   - Activity costs with alternatives
   - Transport fare estimates
   - Meal budget options
   - Accommodation rates
   - Emergency fund allocation\n\n"""

        # Response format with updated fields
        response_format = """{
    "trip_summary": {
        "trip_dates": "string",
        "destination": "string",
        "budget": "string",
        "preferences": "string",
        "must_visit_places": "string",
        "trip_goal": "string"
    },
    "daily_itineraries": [
        {
            "date": "YYYY-MM-DD",
            "activities": [
                {"time": "HH:MM", "description": "activity description"}
            ],
            "meals": [
                {"type": "breakfast/lunch/dinner", "suggestion": "restaurant or meal suggestion"}
            ],
            "transport": [
                {"time": "HH:MM", "description": "transport details"}
            ],
            "accommodation": {
                "name": "hotel/guest house name",
                "address": "area or full address",
                "details": "additional details"
            },
            "weather": {
                "temperature_celsius": "string",
                "condition": "string",
                "precipitation_chance": "string",
                "humidity": "string"
            },
            "weather_summary": {
                "description": "string",
                "recommendations": "string"
            },
            "local_events": [
                {"name": "string", "time": "string", "location": "string"}
            ],
            "daily_route": [
                {
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                    "stop_name": "Location Name"
                }
            ],
            "estimated_costs": {
                "activities": float,
                "meals": float,
                "transport": float,
                "accommodation": float
            }
        }
    ],
    "total_cost": float,
    "recommendations": ["recommendation1", "recommendation2"],
    "weather_forecast": [
        {
            "date": "YYYY-MM-DD",
            "temperature_celsius": "string",
            "condition": "string",
            "precipitation_chance": "string",
            "humidity": "string"
        }
    ]
}"""

        logger.debug("Completed prompt creation")
        return f"{header}{preferences}{data_section}{instructions}Format the response as a JSON object with this structure:\n{response_format}"

    def _generate_weather_based_suggestions(self, weather_conditions: set) -> str:
        """Generate activity suggestions based on weather conditions."""
        suggestions = []
        
        weather_activities = {
            "sunny": [
                "Schedule outdoor activities early morning or late afternoon",
                "Include water-based activities",
                "Plan for shade breaks",
                "Consider indoor alternatives during peak heat"
            ],
            "rainy": [
                "Prioritize indoor cultural activities",
                "Have backup indoor plans for outdoor activities",
                "Include covered transport options",
                "Schedule flexible activities that can be moved"
            ],
            "cloudy": [
                "Ideal for outdoor sightseeing",
                "Good for photography tours",
                "Plan mix of indoor and outdoor activities",
                "Include weather-independent activities"
            ],
            "clear": [
                "Perfect for outdoor adventures",
                "Schedule sunset viewing opportunities",
                "Plan outdoor dining experiences",
                "Include nature-based activities"
            ]
        }
        
        for condition in weather_conditions:
            for weather_type, activities in weather_activities.items():
                if weather_type in condition:
                    suggestions.extend(activities)
                    break
        
        return "\n".join(f"- {suggestion}" for suggestion in set(suggestions))

    def _calculate_event_relevance(
        self,
        event: LocalEvent,
        user_activities: List[str],
        weather_forecast: List[WeatherInfo]
    ) -> float:
        """Calculate how relevant an event is based on user preferences and weather."""
        score = 1.0
        
        # Check if event category matches user activities
        for activity in user_activities:
            if activity.lower() in event.category.lower():
                score += 1.0
        
        # Check weather conditions for the event date
        for weather in weather_forecast:
            if weather.date == event.date:
                # Penalize outdoor events in bad weather
                if "outdoor" in event.description.lower():
                    if "rain" in weather.condition.lower():
                        score -= 0.5
                    if float(weather.precipitation_chance) > 50:
                        score -= 0.5
                break
        
        return score

    def _validate_itinerary_data(self, data: Dict[str, Any]) -> None:
        """Validate the structure of parsed itinerary data."""
        required_fields = ["trip_summary", "daily_itineraries", "recommendations"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValueError(f"Missing required fields in itinerary data: {', '.join(missing_fields)}")
        
        if not isinstance(data["daily_itineraries"], list):
            raise ValueError("daily_itineraries must be a list")
        
        if not data["daily_itineraries"]:
            raise ValueError("daily_itineraries cannot be empty")
        
        for day in data["daily_itineraries"]:
            if not isinstance(day, dict):
                raise ValueError("Each day in daily_itineraries must be a dictionary")
            
            required_day_fields = ["date", "activities", "meals", "transport", "accommodation"]
            missing_day_fields = [field for field in required_day_fields if field not in day]
            
            if missing_day_fields:
                raise ValueError(f"Missing required fields in day data: {', '.join(missing_day_fields)}")

    def _parse_itinerary_response(self, response_text: str, weather_data: WeatherResponse) -> ItineraryResponse:
        """Parse the response from Gemini API into an ItineraryResponse object."""
        try:
            logger.info("Starting to parse itinerary response")
            
            # Clean and validate JSON string
            json_str = self._clean_json_string(response_text)
            
            try:
                data = json.loads(json_str)
                logger.info("Successfully parsed JSON response")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}", exc_info=True)
                # Try one more time with a more aggressive cleanup
                json_str = re.sub(r'[^\x20-\x7E]', '', json_str)  # Remove non-printable chars
                data = json.loads(json_str)
                logger.info("Successfully parsed JSON after aggressive cleanup")
            
            # Validate the structure of parsed data
            self._validate_itinerary_data(data)
            logger.info("Itinerary data structure validation successful")
            
            logger.info("Starting to create itinerary from parsed data")
            daily_itineraries = []
            
            for day_data in data["daily_itineraries"]:
                # Convert datetime objects to strings
                day_date = day_data["date"]
                
                # Find matching weather data or use default
                weather_info = None
                for w in weather_data.weather_forecast:
                    if w.date == day_date:
                        weather_info = w
                        break
                
                if not weather_info:
                    logger.warning(f"No weather data available for {day_date}, using default")
                    weather_info = WeatherInfo(
                        date=day_date,
                        temperature_celsius="0",
                        condition="Unknown",
                        precipitation_chance="0",
                        humidity="0"
                    )
                
                # Create route stops as dictionaries
                daily_route = []
                route_data = day_data.get("daily_route", [])
                if not route_data:
                    daily_route = [{
                        "latitude": 48.8566,  # Default Paris coordinates
                        "longitude": 2.3522,
                        "stop_name": "Default Location"
                    }]
                else:
                    for stop in route_data:
                        daily_route.append({
                            "latitude": float(stop.get("latitude", 48.8566)),
                            "longitude": float(stop.get("longitude", 2.3522)),
                            "stop_name": str(stop.get("stop_name", "Unknown Stop"))
                        })
                
                # Create properly structured objects for the daily itinerary
                activities = [Activity(**act) for act in day_data["activities"]]
                meals = [Meal(**meal) for meal in day_data.get("meals", [])]
                transports = [Transport(**trans) for trans in day_data.get("transport", [])]
                
                # Handle accommodation data with proper validation
                accommodation_data = day_data.get("accommodation", {})
                if not isinstance(accommodation_data, dict):
                    accommodation_data = {}
                
                # Ensure all required fields are present with valid values
                accommodation_data = {
                    "name": str(accommodation_data.get("name", "Default Hotel")),
                    "address": str(accommodation_data.get("address", "City Center")),
                    "details": str(accommodation_data.get("details", "Standard Accommodation"))
                }
                
                try:
                    accommodation = Accommodation(**accommodation_data)
                except Exception as e:
                    logger.warning(f"Error creating accommodation object: {str(e)}")
                    accommodation = Accommodation()  # Use default values
                
                estimated_costs = EstimatedCosts(**day_data.get("estimated_costs", {}))
                weather_summary = WeatherSummary(**day_data.get("weather_summary", {
                    "description": "No data",
                    "recommendations": "No data"
                }))
                
                local_events = [LocalEvent(**event) for event in day_data.get("local_events", [])]
                
                # Create daily itinerary with all required fields
                daily_itinerary = DailyItinerary(
                    date=day_date,
                    activities=activities,
                    meals=meals,
                    transport=transports,
                    accommodation=accommodation,
                    weather=weather_info,
                    estimated_costs=estimated_costs,
                    weather_summary=weather_summary,
                    local_events=local_events,
                    daily_route=daily_route
                )
                daily_itineraries.append(daily_itinerary)
            
            # Calculate total cost
            total_cost = sum(
                sum(cost for cost in day.estimated_costs.dict().values())
                for day in daily_itineraries
            )
            logger.info(f"Total estimated cost: ${total_cost:.2f}")
            
            # Create trip summary
            trip_summary = TripSummary(**data["trip_summary"])
            
            # Create final response
            logger.info("Creating final ItineraryResponse")
            response = ItineraryResponse(
                trip_summary=trip_summary,
                daily_itineraries=daily_itineraries,
                total_cost=total_cost,
                recommendations=data.get("recommendations", []),
                weather_forecast=[{
                    "date": w.date,
                    "temperature_celsius": w.temperature_celsius,
                    "condition": w.condition,
                    "precipitation_chance": w.precipitation_chance,
                    "humidity": w.humidity
                } for w in weather_data.weather_forecast],
                transport_options=[],
                emergency_contacts={
                    "police": "112",
                    "ambulance": "112",
                    "tourist_helpline": "1363"
                },
                useful_phrases={
                    "hello": "Hello",
                    "thank_you": "Thank you",
                    "help": "Help"
                }
            )
            
            logger.info("Successfully created itinerary response")
            return response
        
        except Exception as e:
            logger.error(f"Error parsing itinerary response: {str(e)}", exc_info=True)
            raise 

    def _clean_json_string(self, json_str: str) -> str:
        """Clean and validate JSON string before parsing."""
        try:
            logger.debug("Starting JSON string cleanup")
            
            # Remove any markdown code block syntax
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            
            # Remove trailing commas
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Remove any leading/trailing whitespace
            json_str = json_str.strip()
            
            logger.debug("JSON string cleanup completed")
            return json_str
            
        except Exception as e:
            logger.error(f"Error cleaning JSON string: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to clean JSON string: {str(e)}") 