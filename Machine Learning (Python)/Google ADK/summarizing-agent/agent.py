import asyncio, logging
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
import PyPDF2
import os # Import os to handle paths
from dotenv import load_dotenv # Import load_dotenv

# --- Load Environment Variables --- #
load_dotenv() # Load variables from .env file
# --- End Load Environment Variables --- #

# Define a log file path (e.g., in the current directory)
log_file_path = os.path.join(os.path.dirname(__file__), 'agent_app.log') 

# --- Logging Configuration --- #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file_path, 
    filemode='w' # Changed to overwrite ('w')
)
logging.critical("--- Logging Initialized. Attempting to write to file (overwrite mode). ---")

# --- Set Library Log Levels --- #
# Suppress verbose INFO logs from ADK and GenAI libraries
logging.getLogger("google.adk").setLevel(logging.WARNING)
logging.getLogger("google.genai").setLevel(logging.WARNING)
# Add other library loggers here if needed (e.g., google.api_core)
logging.getLogger("google.api_core").setLevel(logging.WARNING)
# --- End Set Library Log Levels --- #

# --- End Logging Configuration --- #

APP_NAME = "summarizing_agent"
USER_ID = "user123"
SESSION_ID = "session123"
MODEL_NAME = "gemini-2.0-flash-exp"
#MODEL_NAME = "gemini-2.5-pro-exp-03-25"


def read_pdf(file_path: str) -> list[str]: # Return list of pages
    """Reads text content from a PDF file, page by page."""
    pages_text = []
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            logging.info(f"Reading PDF: {file_path} ({len(reader.pages)} pages)")
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text.strip())
                else:
                    logging.warning(f"No text could be extracted from page {i+1} of {file_path}.")
                    pages_text.append("")
        if not any(pages_text):
             logging.warning(f"No text could be extracted from {file_path}. The PDF might be image-based or empty.")
        return pages_text
    except FileNotFoundError:
        logging.error(f"PDF file not found at {file_path}")
        return []
    except Exception as e:
        logging.error(f"Error reading PDF {file_path}: {e}")
        return []

# Function to segment PDF pages
def segment_pdf_text(pages: list[str], segment_size: int = 10) -> list[str]:
    """Segments a list of page texts into chunks of specified size."""
    segments = []
    for i in range(0, len(pages), segment_size):
        min_, max_ = i, i + segment_size
        max_ = min(max_, len(pages))
        segment_pages = pages[min_:max_]
        # Join pages within a segment, adding separators for clarity
        segment_text = "\n\n--- Page Break ---\n\n".join(segment_pages)
        segments.append(segment_text)
    logging.info(f"PDF segmented into {len(segments)} segments of up to {segment_size} pages each.")
    return segments

async def call_agent_async(agent: Agent, query: str, session_service: InMemorySessionService, user_id: str, session_id: str) -> str:
    """Sends a query to a specific agent and returns the final response text."""
    # logging.info(f"Calling Agent: {agent.name} with Query: {query[:100]}...") # Original line - commented out
    logging.info(f"Calling Agent: {agent.name}") # Modified: Log only agent name

    # Create a runner for the specific agent
    runner = Runner(
        agent=agent,
        app_name=APP_NAME, # Use the global APP_NAME
        session_service=session_service, # Pass the session service
    )

    # Prepare the user's message in ADK format
    content = types.Content(role='user', parts=[types.Part(text=query)])
    final_response_text = f"Agent {agent.name} did not produce a final response." # Default

    try:
        # Use the passed user_id and session_id
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {content}") # Keep commented unless debugging
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    final_response_text = f"Agent {agent.name} escalated: {event.error_message or 'No specific message.'}"
                break
    except Exception as e:
        logging.error(f"Error during agent call ({agent.name}): {e}")
        final_response_text = f"Error occurred while calling agent {agent.name}."

    logging.info(f"Agent {agent.name} Response: {final_response_text[:100]}...")
    return final_response_text

# New function to process a single segment
async def process_pdf_segment(segment_text: str, accumulated_previous_summaries: str, session_service: InMemorySessionService, user_id: str, session_id: str) -> tuple[str, str]:
    """Runs the 3-agent pipeline for a single PDF segment and returns final summary and critique."""

    # --- Call Agent 1 (First Pass Summary) --- #
    logging.info("Segment Step 1: Calling First Pass Summarizer")
    prompt_agent1 = f"Summarize the following text excerpt from a PDF segment:\n\n{segment_text}"
    summary1 = await call_agent_async(agent_first_pass, prompt_agent1, session_service, user_id, session_id)

    # --- Call Agent 2 (Second Pass Summary + Context) --- #
    logging.info("Segment Step 2: Calling Second Pass Summarizer")
    prompt_agent2 = f"Original Text Segment:\n{segment_text}\n\nFirst Summary of this Segment:\n{summary1}\n\nSummaries of ALL Previous Segments (for context only):\n{accumulated_previous_summaries or 'N/A - This is the first segment.'}"
    summary2 = await call_agent_async(agent_second_pass, prompt_agent2, session_service, user_id, session_id)

    # --- Call Agent 3 (Fact Check + Context) --- #
    logging.info("Segment Step 3: Calling Fact Checker/Critic")
    prompt_agent3 = f"Original Text Segment:\n{segment_text}\n\nFinal Summary of this Segment:\n{summary2}\n\nSummaries of ALL Previous Segments (for context only):\n{accumulated_previous_summaries or 'N/A - This is the first segment.'}"
    critique = await call_agent_async(agent_fact_check, prompt_agent3, session_service, user_id, session_id)

    return summary2, critique # Return final summary and critique for this segment

# --- Agent Definitions (Instructions Updated slightly for clarity) --- #
agent_first_pass = Agent(
    name="agent_first_pass",
    model=MODEL_NAME,
    description=(
        "Agent to give a first pass summary of a text excerpt from a PDF segment."
    ),
    instruction=(
        "I have sent you a text excerpt from a 10-page segment of a PDF. Preserve all original ideas while making the content shorter and clearer. Match the tone of the original. Focus on the main ideas and arguments for THIS SEGMENT, without repetition or needless stories. Return only the full summary text for this segment."
    ),
)

agent_second_pass = Agent(
    name="agent_second_pass",
    model=MODEL_NAME,
    description=(
        "Agent to refine the first pass summary of a PDF segment, using previous context."
    ),
    instruction=(
        "I have sent you: (1) the original text from a 10-page PDF segment, (2) a first-pass summary of THIS segment, and (3) the CONCATENATED final summaries of ALL PREVIOUS segments (if any). "
        "Compare the first-pass summary (2) to the original text segment (1). Does the summary leave anything important out from THIS segment? If so, add the missing information. Remove any unimportant or redundant information from the summary. "
        "Use the previous segments' summaries (3) only for context if needed to ensure flow or understand references, but focus primarily on accurately and concisely summarizing THIS current segment (1). "
        "Ensure the summary maintains the original's tone. Return only the final, revised summary text for THIS segment."
    ),
)

agent_fact_check = Agent(
    name="agent_fact_check",
    model=MODEL_NAME,
    description=(
        "Agent that acts as a critic of the second pass summary for a segment, using previous context."
    ),
    instruction=(
        "I have sent you: (1) the original text from a 10-page PDF segment, (2) the final summary of THIS segment, and (3) the CONCATENATED final summaries of ALL PREVIOUS segments (if any). "
        "Fact check the final summary (2) against the original text segment (1). Rate its conciseness, accuracy, and completeness FOR THIS SEGMENT. "
        "You can refer to the previous segments' summaries (3) for context if necessary. Give the result in a table format. Do not return the summary itself, only the evaluation table for THIS segment."
    ),
)

session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)
logging.info(f"ADK Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

# New Interactive Workflow Function
async def run_interactive_workflow(pdf_path: str):
    """Reads a PDF, segments it, and processes segments interactively.
    NOTE: This function is designed for testing the logic locally.
    It uses blocking input() and reads from a file path.
    Adaptation is needed for actual ADK chat integration.
    """
    logging.info(f"Starting Interactive PDF Summary Workflow for: {pdf_path}")

    pdf_pages = read_pdf(pdf_path)
    if not pdf_pages:
        logging.error("Workflow aborted: Could not read PDF text.")
        return

    pdf_segments = segment_pdf_text(pdf_pages, segment_size=10)
    if not pdf_segments:
        logging.warning("Workflow aborted: No segments created.")
        return

    # Store all summaries generated so far in a list
    all_segment_summaries = [] 

    for i, segment in enumerate(pdf_segments):
        logging.info(f"Processing Segment {i+1}/{len(pdf_segments)}")

        # Prepare the accumulated context from previous summaries
        # Join summaries with a clear separator
        accumulated_context = "\n\n--- End of Previous Segment Summary ---\n\n".join(all_segment_summaries)

        # Process the current segment using the 3-agent pipeline
        final_summary, critique = await process_pdf_segment(
            segment_text=segment,
            accumulated_previous_summaries=accumulated_context, # Pass accumulated context
            session_service=session_service, 
            user_id=USER_ID,                 
            session_id=SESSION_ID             
        )

        # --- Log Results for the Segment --- # 
        logging.info(f"Results for Segment {i+1}")
        # Log summary and critique (Full content)
        logging.info(f"Final Summary (Agent 2) for Segment {i+1}:\n{final_summary}")
        logging.info(f"Critique (Agent 3) for Segment {i+1}:\n{critique}")

        # Store results 
        all_segment_summaries.append(final_summary) # Add current summary to the list

        # --- Ask User to Proceed (Simulation - ONLY works when run directly) --- #
        if i < len(pdf_segments) - 1: # Don't ask after the last segment
            logging.info("--- Interactive Prompt Simulation (will block if run directly) ---")
            while True:
                # This input() part will NOT work correctly via adk web
                try:
                    #proceed = input(f"Proceed to next segment ({i+2}/{len(pdf_segments)})? (yes/no): ").lower().strip()
                    proceed = 'yes'
                    if proceed == 'yes' or proceed == 'y':
                        break
                    elif proceed == 'no' or proceed == 'n':
                        logging.info("Workflow stopped by user.")
                        # Log combined results so far if needed
                        logging.info("Combined Summaries So Far:\n" + "\n\n---\n\n".join(all_segment_summaries)) # Use the list here too
                        return # Exit the workflow function
                    else:
                        print("Invalid input. Please enter 'yes' or 'no'.") # Keep print for direct input feedback
                except RuntimeError:
                    logging.warning("input() called in non-interactive context (e.g., adk web). Cannot simulate interaction.")
                    # Decide how to proceed in non-interactive mode, e.g., process all segments automatically?
                    logging.info("Auto-proceeding to next segment as interaction is not possible.")
                    break # Automatically proceed if input() fails
        else:
            logging.info("All segments processed. Workflow Complete.")
            # Log combined final results if needed
            logging.info("Final Combined Summary:\n" + "\n\n---\n\n".join(all_segment_summaries)) # Use the list here too

async def main():
    # Replace with the actual path to your PDF file for this script
    # In a real ADK app, the PDF content/path would come from the chat
    pdf_file_path = "Tese de Mestrado.pdf" # <<< IMPORTANT: UPDATE THIS PATH
    await run_interactive_workflow(pdf_file_path)

if __name__ == "__main__":
    # Basic asyncio setup to run the main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
