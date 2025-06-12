import threading
import re
import json
from google import genai
from socratic_agent.core.config import API_KEY, GENAI_MODEL, FALLBACK_GENAI_MODEL

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


async def get_llm_response(prompt: str, model_name: str = GENAI_MODEL) -> tuple[str, str]:
    """
    Generates a response from the Google GenAI model (synchronous).

    Args:
        prompt: The prompt to send to the LLM.
        model_name: The name of the model to use, defaults to GENAI_MODEL.

    Returns:
        A tuple of (response_text, model_name) where response_text is the generated text response
        and model_name is the name of the model that generated it.
    """
    try:
        llm_client = _get_llm_client()
    except Exception as e:
        raise RuntimeError(f"Error initializing LLM client: {e}")

    try:
        response = await llm_client.aio.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        if hasattr(response, 'text'):
            return response.text, model_name
        else:
            raise ValueError("LLM response had no .text attribute")
    
    except genai.errors.ServerError as e:
        if model_name == GENAI_MODEL:
            return await get_llm_response(prompt, FALLBACK_GENAI_MODEL)
        
        # Handle specific server errors
        if hasattr(e, 'status') and e.status == 'UNAVAILABLE':
            raise RuntimeError("LLM service is temporarily overloaded. Please try again in a few moments.")
        elif hasattr(e, 'status') and e.status == 'RESOURCE_EXHAUSTED':
            raise RuntimeError("Rate limit exceeded. Please try again later.")
        else:
            # For other server errors, try to extract useful info
            error_msg = str(e)
            if '{' in error_msg and '}' in error_msg:
                try:
                    # Try to parse the error JSON if present
                    json_str = error_msg[error_msg.find('{'):error_msg.rfind('}')+1]
                    data = json.loads(json_str)
                    if 'error' in data and 'message' in data['error']:
                        raise RuntimeError(f"Server error: {data['error']['message']}")
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(f"Server error: {error_msg}")
            
    except Exception as e:
        if model_name == GENAI_MODEL:
            return await get_llm_response(prompt, FALLBACK_GENAI_MODEL)
        raise RuntimeError(f"Error generating LLM response: {e}")