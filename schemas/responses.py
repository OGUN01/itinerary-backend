from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

class RouteStop(BaseModel):
    latitude: float
    longitude: float
    stop_name: str

    def dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "stop_name": self.stop_name
        }

class TransportOption(BaseModel):
    mode: str = Field(default="Unknown", description="Mode of transport (e.g., train, bus, flight)")
    provider: str = Field(default="Unknown", description="Transport service provider")
    departure: str = Field(default="", description="Departure time in YYYY-MM-DD HH:MM format")
    arrival: str = Field(default="", description="Arrival time in YYYY-MM-DD HH:MM format")
    price: str = Field(default="0.00", description="Price in USD")
    duration: str = Field(default="0", description="Duration of journey")
    details: str = Field(default="", description="Additional transport details")

    @validator('departure', 'arrival')
    def validate_datetime(cls, v: str) -> str:
        """Validate datetime strings are in correct format or empty."""
        if not v:
            return ""
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M")
            return v
        except ValueError:
            return ""

    @validator('price')
    def validate_price(cls, v: str) -> str:
        """Ensure price is a valid string representation of a number."""
        if not v:
            return "0.00"
        try:
            float(v)
            return v
        except ValueError:
            return "0.00"

    @validator('duration')
    def validate_duration(cls, v: str) -> str:
        """Ensure duration is a valid string."""
        if not v:
            return "0"
        return v

class TransportResponse(BaseModel):
    options: List[TransportOption]

class WeatherInfo(BaseModel):
    date: str
    temperature_celsius: str
    condition: str
    precipitation_chance: str
    humidity: str

class LocalEvent(BaseModel):
    name: str
    date: str
    venue: str
    category: str
    description: str = ""
    price_range: str = ""

class Activity(BaseModel):
    time: str
    description: str

class Meal(BaseModel):
    type: str
    suggestion: str

class Transport(BaseModel):
    time: str
    description: str

class Accommodation(BaseModel):
    name: str = Field(default="Default Hotel", description="Name of the accommodation")
    address: str = Field(default="City Center", description="Address of the accommodation")
    details: str = Field(default="Standard Accommodation", description="Additional details about the accommodation")

    @validator('name', 'address', 'details')
    def validate_string_fields(cls, v: str) -> str:
        """Ensure string fields are never None and have default values."""
        if not v or v is None:
            return cls.__fields__[cls.__fields_set__.pop()].default
        return v

class WeatherSummary(BaseModel):
    description: str
    recommendations: str

class EstimatedCosts(BaseModel):
    activities: float = 0.0
    meals: float = 0.0
    transport: float = 0.0
    accommodation: float = 0.0

class DailyItinerary(BaseModel):
    date: str
    activities: List[Activity]
    meals: List[Meal]
    transport: List[Transport]
    accommodation: Accommodation
    weather: WeatherInfo
    estimated_costs: EstimatedCosts
    weather_summary: WeatherSummary
    local_events: List[LocalEvent] = []
    daily_route: List[Dict[str, Union[float, str]]]

class TripSummary(BaseModel):
    trip_dates: str
    destination: str
    budget: str
    preferences: str
    must_visit_places: str
    trip_goal: str

class WeatherResponse(BaseModel):
    weather_forecast: List[WeatherInfo]
    local_events: List[LocalEvent] = []

class ItineraryResponse(BaseModel):
    trip_summary: TripSummary
    daily_itineraries: List[DailyItinerary]
    total_cost: float
    recommendations: List[str]
    weather_forecast: List[Dict[str, str]]
    transport_options: List[Dict[str, str]] = []
    emergency_contacts: Dict[str, str]
    useful_phrases: Dict[str, str] 