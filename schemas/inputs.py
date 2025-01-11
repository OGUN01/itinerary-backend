from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, datetime

class TravelInput(BaseModel):
    origin: str = Field(..., description="Starting location of the trip")
    destination: str = Field(..., description="Destination location of the trip")
    start_date: str = Field(..., description="Start date of the trip (YYYY-MM-DD)")
    return_date: str = Field(..., description="Return date of the trip (YYYY-MM-DD)")

    @validator('start_date', 'return_date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

class UserPreferences(BaseModel):
    budget: float = Field(..., description="Total budget for the trip in USD")
    activities: List[str] = Field(default_factory=list, description="List of preferred activities")
    meal_preferences: List[str] = Field(default_factory=list, description="List of dietary preferences")
    preferred_places: List[str] = Field(default_factory=list, description="List of must-visit places")
    transport_preferences: Optional[List[str]] = Field(
        default_factory=list,
        description="Preferred modes of transport (e.g., ['flight', 'train', 'bus'])"
    )
    accommodation_type: Optional[str] = Field(
        None,
        description="Preferred type of accommodation (e.g., hotel, hostel, apartment)"
    ) 