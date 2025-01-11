from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
import random
import logging
from ..schemas.responses import (
    TransportOption, TransportResponse, WeatherResponse,
    Activity, Meal, Transport, Accommodation, WeatherInfo,
    WeatherSummary, EstimatedCosts, LocalEvent, DailyItinerary,
    TripSummary, ItineraryResponse
)
from ..agents.transport_agent import TransportAgent
from ..agents.weather_agent import WeatherAgent
from ..agents.itinerary_generator_agent import ItineraryGeneratorAgent
from ..schemas.inputs import TravelInput, UserPreferences
import os
import json

logger = logging.getLogger(__name__)

router = APIRouter(tags=["itinerary"])

@router.get("/health")
async def health_check():
    """Health check endpoint to verify API status."""
    try:
        # Check if agents are initialized
        if not all([transport_agent, weather_agent, itinerary_agent]):
            raise HTTPException(
                status_code=503,
                detail={"status": "error", "message": "One or more agents not initialized"}
            )
        
        # Check environment variables
        required_env_vars = ["GEMINI_API_KEY", "WEATHER_API_KEY", "TICKETMASTER_API_KEY"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "message": f"Missing environment variables: {', '.join(missing_vars)}"
                }
            )
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Internal server error during health check"}
        )

# Initialize agents
transport_agent = TransportAgent()
weather_agent = WeatherAgent()
itinerary_agent = ItineraryGeneratorAgent()

class ItineraryRequest(BaseModel):
    travel_input: TravelInput
    user_preferences: UserPreferences

@router.post("/itinerary", response_model=ItineraryResponse)
async def generate_itinerary(request: ItineraryRequest):
    """
    Generate a travel itinerary based on user preferences and travel input.
    """
    request_id = f"{request.travel_input.destination}_{request.travel_input.start_date}_{request.travel_input.return_date}"
    logger.info(f"Processing itinerary request {request_id}")
    
    try:
        logger.info(f"Starting itinerary generation for destination: {request.travel_input.destination}")
        logger.debug(f"Full request data: {request.model_dump_json()}")

        # Step 1: Get weather and events data
        logger.info("Fetching weather and events data...")
        weather_response = await weather_agent.get_weather_and_events(request.travel_input)
        if not weather_response or not weather_response.weather_forecast:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Failed to fetch weather data",
                    "type": "WEATHER_ERROR"
                }
            )
        logger.info(f"Received weather data with {len(weather_response.weather_forecast)} days forecast")
        logger.info(f"Received {len(weather_response.local_events)} local events")
        logger.debug(f"Weather response: {weather_response.model_dump_json()}")

        # Step 2: Get transport options
        logger.info("Fetching transport options...")
        transport_response = await transport_agent.get_transport_options(request.travel_input)
        if not transport_response or not transport_response.options:
            logger.warning("No transport options available")
        else:
            logger.info(f"Received {len(transport_response.options)} transport options")
            logger.debug(f"Transport response: {transport_response.model_dump_json()}")

        # Step 3: Generate itinerary using weather data and transport options
        logger.info("Generating detailed itinerary...")
        try:
            itinerary = await itinerary_agent.generate_itinerary(
                travel_input=request.travel_input,
                user_preferences=request.user_preferences,
                weather_data=weather_response
            )
            logger.info("Itinerary generation completed successfully")
            logger.debug(f"Generated itinerary: {itinerary.model_dump_json()}")

            # Add transport options to the response
            if transport_response and transport_response.options:
                itinerary.transport_options = [
                    {
                        "mode": str(option.mode),
                        "provider": str(option.provider),
                        "departure": str(option.departure),
                        "arrival": str(option.arrival),
                        "price": str(option.price),
                        "duration": str(option.duration),
                        "details": option.details if isinstance(option.details, str) else json.dumps(option.details, ensure_ascii=False)
                    }
                    for option in transport_response.options
                ]
                logger.info("Successfully added transport options to itinerary")
            
            return itinerary

        except ValueError as e:
            logger.error(f"Validation error in itinerary generation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=422,
                detail={
                    "message": str(e),
                    "type": "VALIDATION_ERROR"
                }
            )
        except Exception as e:
            logger.error(f"Error generating itinerary: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Failed to generate itinerary",
                    "error": str(e),
                    "type": "GENERATION_ERROR"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_itinerary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred",
                "error": str(e),
                "type": "UNEXPECTED_ERROR"
            }
        ) 