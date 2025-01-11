import requests
import json

# Test data
test_request = {
    "travel_input": {
        "origin": "New York",
        "destination": "Paris",
        "start_date": "2025-02-01",
        "return_date": "2025-02-05"
    },
    "user_preferences": {
        "budget": 2000,
        "activities": ["sightseeing", "museums", "food"],
        "meal_preferences": ["local cuisine"],
        "preferred_places": ["Eiffel Tower", "Louvre"],
        "transport_preferences": ["metro", "walk"],
        "accommodation_type": "hotel"
    }
}

# Send request
try:
    response = requests.post(
        "http://localhost:8000/api/itinerary",
        json=test_request,
        headers={"Content-Type": "application/json"}
    )
    
    # Print status code and headers
    print(f"Status Code: {response.status_code}")
    print("\nResponse Headers:")
    for header, value in response.headers.items():
        print(f"{header}: {value}")
    
    # Print response
    print("\nResponse Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
        
except Exception as e:
    print(f"Error: {str(e)}") 