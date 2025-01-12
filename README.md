# Backend Documentation - Travel Itinerary Generator

## Project Structure
```
backend/
├── agents/                    # AI Agents for different services
│   ├── event_agent.py        # Event planning and recommendations
│   ├── itinerary_agent.py    # Itinerary generation logic
│   └── weather_agent.py      # Weather analysis and forecasting
│
├── routers/                  # FastAPI route handlers
│   ├── events.py            # Event-related endpoints
│   ├── itinerary.py         # Itinerary management endpoints
│   └── weather.py           # Weather information endpoints
│
├── schemas/                  # Pydantic models and validators
│   ├── events.py            # Event data models
│   ├── itinerary.py         # Itinerary data models
│   └── weather.py           # Weather data models
│
├── utils/                    # Utility functions and helpers
│   ├── api_clients.py       # External API client wrappers
│   ├── validators.py        # Custom data validators
│   └── helpers.py           # Common helper functions
│
├── tests/                    # Test suite
│   ├── test_events.py       # Event endpoint tests
│   ├── test_itinerary.py    # Itinerary endpoint tests
│   └── test_weather.py      # Weather endpoint tests
│
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
└── pytest.ini              # Pytest configuration
```

## Technology Stack
- FastAPI (Web Framework)
- Pydantic (Data Validation)
- SQLAlchemy (ORM)
- Pytest (Testing)
- Google Gemini (AI/ML)
- Railway (Deployment)

## Core Features

### 1. AI-Powered Itinerary Generation
- Smart event planning
- Weather-aware scheduling
- Budget optimization
- Location-based recommendations

### 2. External API Integration
- Weather services
- Event ticketing
- Transport booking
- Location services

### 3. Data Processing
- Input validation
- Response formatting
- Error handling
- Cache management

## API Documentation

### Endpoints Structure
- `/api/v1/itinerary/`: Itinerary management
- `/api/v1/events/`: Event operations
- `/api/v1/weather/`: Weather information

## Development Guidelines

### 1. Code Organization
- Modular architecture
- Clear separation of concerns
- Type hints mandatory
- Comprehensive documentation

### 2. Testing Requirements
- Unit tests for all endpoints
- Integration tests for flows
- Minimum 90% coverage
- Performance testing

### 3. Security Practices
- API key management
- Rate limiting
- Input sanitization
- Error handling

## Deployment

### Railway Configuration
- Auto-deployment from main branch
- Environment variables
- Health checks
- Rollback capability

## Monitoring
- Error tracking
- Performance metrics
- API usage statistics
- Response time monitoring 