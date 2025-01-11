from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
import uuid
import re
from math import radians, sin, cos, sqrt, atan2

router = APIRouter(prefix="/events", tags=["events"])

VALID_CATEGORIES = ["Music", "Sports", "Arts", "Food", "Theater", "Festival", "Exhibition"]
PRICE_RANGE_PATTERN = re.compile(r'^\$\d+(?:\s*-\s*\$\d+)?$|^Free$')

class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    date: datetime = Field(..., description="Event date and time")
    venue: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., description="Event category")
    price_range: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    coordinates: Optional[Coordinates] = Field(None, description="Event location coordinates")

    @validator('date')
    def validate_date(cls, v):
        if v < datetime.now():
            raise ValueError("Event date must be in the future")
        return v

    @validator('category')
    def validate_category(cls, v):
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")
        return v

    @validator('price_range')
    def validate_price_range(cls, v):
        if v is not None and not PRICE_RANGE_PATTERN.match(v):
            raise ValueError("Invalid price range format. Must be like '$10', '$10 - $20', or 'Free'")
        return v

class Event(EventCreate):
    id: str = Field(..., description="Unique event identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Summer Music Festival",
                "date": "2025-01-10T18:00:00",
                "venue": "City Park",
                "category": "Music",
                "price_range": "$20 - $50",
                "description": "Annual summer music festival",
                "coordinates": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            }
        }

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate the distance between two coordinates using the Haversine formula.
    Returns distance in kilometers.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

# Thread-safe in-memory storage (for development)
from threading import Lock
events_lock = Lock()
events_db: List[Event] = []

@router.get("", response_model=List[Event])
async def get_events(
    start_date: Optional[datetime] = Query(None, description="Filter events after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events before this date"),
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Location latitude"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Location longitude"),
    radius: Optional[float] = Query(None, gt=0, le=100, description="Search radius in kilometers"),
    categories: Optional[List[str]] = Query(None, description="Filter events by categories"),
    limit: Optional[int] = Query(10, gt=0, le=100, description="Maximum number of events to return")
):
    """
    Get a list of events with optional filtering.
    """
    with events_lock:
        filtered_events = events_db.copy()

    # Validate categories
    if categories:
        invalid_categories = [c for c in categories if c not in VALID_CATEGORIES]
        if invalid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid categories: {', '.join(invalid_categories)}"
            )

    # Apply filters
    if start_date:
        filtered_events = [e for e in filtered_events if e.date >= start_date]
    if end_date:
        if end_date < start_date:
            raise HTTPException(
                status_code=400,
                detail="end_date must be after start_date"
            )
        filtered_events = [e for e in filtered_events if e.date <= end_date]
    if categories:
        filtered_events = [e for e in filtered_events if e.category in categories]

    # Apply location-based filtering
    if all(x is not None for x in [latitude, longitude, radius]):
        filtered_events = [
            event for event in filtered_events
            if event.coordinates and calculate_distance(
                (latitude, longitude),
                (event.coordinates.latitude, event.coordinates.longitude)
            ) <= radius
        ]

    # Sort by date and distance if location provided
    if latitude is not None and longitude is not None:
        filtered_events.sort(key=lambda x: (
            x.date,
            calculate_distance(
                (latitude, longitude),
                (x.coordinates.latitude, x.coordinates.longitude)
            ) if x.coordinates else float('inf')
        ))
    else:
        filtered_events.sort(key=lambda x: x.date)

    # Apply limit
    return filtered_events[:limit]

@router.post("", response_model=Event, status_code=201)
async def create_event(event: EventCreate):
    """
    Create a new event.
    """
    # Generate UUID
    event_id = str(uuid.uuid4())
    
    # Create new event
    new_event = Event(
        id=event_id,
        **event.model_dump()
    )
    
    # Thread-safe append
    with events_lock:
        events_db.append(new_event)
    
    return new_event

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str):
    """
    Get a specific event by ID.
    """
    try:
        uuid.UUID(event_id)  # Validate UUID format
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    with events_lock:
        event = next((e for e in events_db if e.id == event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event

@router.put("/{event_id}", response_model=Event)
async def update_event(event_id: str, event_update: EventCreate):
    """
    Update an existing event.
    """
    try:
        uuid.UUID(event_id)  # Validate UUID format
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    with events_lock:
        event_idx = next((i for i, e in enumerate(events_db) if e.id == event_id), None)
        if event_idx is None:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update event
        updated_event = Event(
            id=event_id,
            **event_update.model_dump()
        )
        events_db[event_idx] = updated_event
    
    return updated_event

@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str):
    """
    Delete an event.
    """
    try:
        uuid.UUID(event_id)  # Validate UUID format
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    with events_lock:
        event_idx = next((i for i, e in enumerate(events_db) if e.id == event_id), None)
        if event_idx is None:
            raise HTTPException(status_code=404, detail="Event not found")
        
        events_db.pop(event_idx)
    
    return None 