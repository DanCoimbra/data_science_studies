import datetime, asyncio, warnings, logging
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

#warnings.filterwarnings("ignore")
#logging.basicConfig(level=logging.ERROR)


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.
    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").
    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---")
    city_normalized = city.lower().replace(" ", "") # Basic input normalization
    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25°C."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15°C."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."},
    }
    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {"status": "error", "error_message": f"Sorry, I don't have weather information for '{city}'."}


# @title Define Agent Interaction Function
async def call_agent_async(query: str):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")
  # Prepare the user's message in ADK format
  content = types.Content(role='user', parts=[types.Part(text=query)])
  final_response_text = "Agent did not produce a final response." # Default
  # Key Concept: run_async executes the agent logic and yields Events.
  # We iterate through events to find the final answer.
  async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
      # You can uncomment the line below to see *all* events during execution
      print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found
  print(f"<<< Agent Response: {final_response_text}")


root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash-exp",
    description=(
        "Agent to answer questions about weather in a city."
    ),
    instruction=(
        "I can answer your questions about weather in a city."
    ),
    tools=[get_weather],
)


APP_NAME = "weather_time_agent"
USER_ID = "user123"
SESSION_ID = "session123"
session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)
print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")


runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)
print(f"Runner created for agent '{runner.agent.name}'.")
