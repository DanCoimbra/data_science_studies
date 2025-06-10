import threading
from google import genai
from socratic_agent.core.config import API_KEY

_client = None
_client_lock = threading.Lock()


def _get_llm_client():
    """Initializes and returns the genai.Client, creating it only if it doesn't exist."""
    global _client

    if API_KEY is None:
        raise ValueError("API_KEY is not set.")
    
    with _client_lock:
        if _client is None:
            try:
                _client = genai.Client(api_key=API_KEY)
            except Exception as e:
                raise RuntimeError(f"Failed to create genai.Client: {e}")

    return _client


def get_llm_response(prompt: str) -> str:
    """
    Generates a response from the Google GenAI model (synchronous).

    Args:
        prompt: The prompt to send to the LLM.

    Returns:
        The generated text response, or an error message if something goes wrong.
    """
    llm_client = _get_llm_client()
    if not llm_client:
        return "LLM client not configured or failed to initialize."

    try:
        response = llm_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        if hasattr(response, 'text'):
            return response.text
        else:
            return "LLM response had no .text attribute"

    except Exception as e:
        return f"Error generating LLM response: {e}" 