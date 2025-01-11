import asyncio
from datetime import date, timedelta
from src.agents.transport_agent import TransportAgent
from src.agents.weather_agent import WeatherAgent
from src.agents.itinerary_generator_agent import ItineraryGeneratorAgent
from src.schemas.inputs import TravelInput, UserPreferences

async def test_all_agents():
    print("\n=== Testing All Agents ===\n")
    
    # Create test input data
    travel_input = TravelInput(
        origin="Gurugram",
        destination="Jaipur",
        start_date=date.today() + timedelta(days=30),  # Plan for a month from now
        return_date=date.today() + timedelta(days=35)  # 5-day trip
    )
    
    user_preferences = UserPreferences(
        budget=2000.0,
        activities=["sightseeing", "historical places", "shopping"],
        meal_preferences=["local cuisine", "vegetarian options", "rajasthani food"],
        preferred_places=["Hawa Mahal", "Amber Fort", "City Palace"],
        transport_preferences=["train", "bus", "cab"],
        accommodation_type="hotel"
    )
    
    try:
        # 1. Test Transport Agent
        print("Testing Transport Agent...")
        transport_agent = TransportAgent()
        transport_result = await transport_agent.get_transport_options(travel_input)
        print(f"\nFound {len(transport_result.options)} transport options:")
        for option in transport_result.options:
            print(f"- {option.mode} by {option.provider}: ${option.price}")
        print("\n" + "="*50 + "\n")
        
        # 2. Test Weather Agent
        print("Testing Weather Agent...")
        weather_agent = WeatherAgent()
        weather_result = await weather_agent.get_weather_and_events(travel_input)
        print(f"\nWeather forecast for {len(weather_result.weather_forecast)} days:")
        for weather in weather_result.weather_forecast:
            print(f"- {weather.date.date()}: {weather.condition}, {weather.temperature_celsius}°C")
        
        print(f"\nFound {len(weather_result.local_events)} local events:")
        for event in weather_result.local_events:
            print(f"- {event.name} at {event.venue} on {event.date.date()}")
        print("\n" + "="*50 + "\n")
        
        # 3. Test Itinerary Generator Agent
        print("Testing Itinerary Generator Agent...")
        itinerary_agent = ItineraryGeneratorAgent()
        itinerary_result = await itinerary_agent.generate_itinerary(
            travel_input,
            user_preferences,
            weather_result
        )
        
        print("\nTrip Summary:")
        for key, value in itinerary_result.trip_summary.items():
            print(f"- {key}: {value}")
        
        print("\nDaily Itineraries:")
        for day in itinerary_result.daily_itineraries:
            print(f"\nDay {day.date.date()}:")
            print("Activities:")
            for activity in day.activities:
                print(f"  - {activity['time']}: {activity['description']}")
            print("Meals:")
            for meal in day.meals:
                print(f"  - {meal['type']}: {meal['suggestion']}")
            print(f"Weather: {day.weather.condition}, {day.weather.temperature_celsius}°C")
            print(f"Daily Cost Estimate: ${sum(day.estimated_costs.values())}")
        
        print(f"\nTotal Trip Cost: ${itinerary_result.total_cost}")
        print("\nRecommendations:")
        for rec in itinerary_result.recommendations:
            print(f"- {rec}")
            
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_all_agents()) 