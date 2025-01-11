# Itinerary Generator Backend

FastAPI backend service for generating personalized travel itineraries using Google's Gemini API.

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key
WEATHER_API_KEY=your_weather_api_key
TICKETMASTER_API_KEY=your_ticketmaster_api_key
```

5. Run the development server:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment

This backend is configured for deployment on Railway. See `railway.json` for configuration details. 