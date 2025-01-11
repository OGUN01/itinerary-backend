import google.generativeai as genai
from typing import List, Dict
import os
import json
from datetime import datetime, timedelta
import logging
from ..schemas.inputs import TravelInput
from ..schemas.responses import TransportOption, TransportResponse
import re

logger = logging.getLogger(__name__)

class TransportAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def get_transport_options(self, travel_input: TravelInput) -> TransportResponse:
        """Get transport options for the given travel input."""
        try:
            logger.info(f"Getting transport options from {travel_input.origin} to {travel_input.destination}")
            
            if not travel_input.origin or not travel_input.destination:
                raise ValueError("Origin and destination are required")
                
            prompt = self._create_transport_prompt(travel_input)
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                logger.error("Empty response from transport API")
                raise ValueError("Failed to get transport options")
                
            transport_options = self._parse_transport_response(response.text)
            
            if not transport_options:
                logger.warning("No transport options found")
                return TransportResponse(options=[])
                
            logger.info(f"Successfully retrieved {len(transport_options)} transport options")
            return TransportResponse(options=transport_options)
        
        except ValueError as e:
            logger.error(f"Validation error in TransportAgent: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in TransportAgent: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get transport options: {str(e)}")

    def _create_transport_prompt(self, travel_input: TravelInput) -> str:
        """Create prompt for transport options."""
        try:
            # Dates are already in YYYY-MM-DD format from TravelInput validation
            start_date_str = travel_input.start_date
            return_date_str = travel_input.return_date
            
            logger.debug(f"Creating transport prompt for dates: {start_date_str} to {return_date_str}")
            
            return f"""
            As a travel transport expert, suggest the best transport options between {travel_input.origin} and {travel_input.destination}
            for travel dates from {start_date_str} to {return_date_str}.
            
            Please provide multiple options including trains, buses, and cabs where available.
            For each option, include:
            - Mode of transport
            - Provider name (e.g., Indian Railways, Rajasthan State Transport, Ola, Uber)
            - Departure and arrival times
            - Price in USD
            - Duration
            - Additional details (route information, stops, amenities, etc.)
            
            Format the response as a JSON array of transport options.
            Each option should follow this structure:
            {{
                "mode": "string",
                "provider": "string",
                "departure_time": "YYYY-MM-DD HH:MM",
                "arrival_time": "YYYY-MM-DD HH:MM",
                "price": "0.00",
                "duration_minutes": "0",
                "details": {{
                    "route": "string",
                    "stops": ["stop1", "stop2"],
                    "amenities": "string",
                    "class": "string",
                    "notes": "string"
                }}
            }}
            """
        except Exception as e:
            logger.error(f"Error creating transport prompt: {str(e)}", exc_info=True)
            raise ValueError("Failed to create transport prompt")

    def _parse_transport_response(self, response_text: str) -> List[TransportOption]:
        """Parse the transport options from the API response."""
        try:
            # Extract JSON from the response text
            json_str = response_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            
            # Remove trailing commas and clean the JSON
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                raise ValueError("Invalid transport data format")
            
            if not isinstance(data, list):
                raise ValueError("Transport data must be a list")
                
            logger.debug(f"Parsed transport data: {data}")
            
            # Convert each option to TransportOption model
            transport_options = []
            for option in data:
                try:
                    # Validate required fields
                    required_fields = ["mode", "provider", "departure_time", "arrival_time", "price", "duration_minutes"]
                    missing_fields = [field for field in required_fields if field not in option]
                    if missing_fields:
                        logger.warning(f"Skipping transport option due to missing fields: {missing_fields}")
                        continue
                        
                    # Format fields as strings according to frontend expectations
                    transport_option = TransportOption(
                        mode=str(option["mode"]),
                        provider=str(option["provider"]),
                        departure=str(option["departure_time"]),
                        arrival=str(option["arrival_time"]),
                        price=str(float(option["price"])),
                        duration=str(option["duration_minutes"]),
                        details=json.dumps(option.get("details", {}), ensure_ascii=False)
                    )
                    transport_options.append(transport_option)
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Invalid transport option data: {str(e)}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error processing transport option: {str(e)}")
                    continue
            
            return transport_options
        
        except ValueError as e:
            logger.error(f"Validation error parsing transport response: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error parsing transport response: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse transport options: {str(e)}") 