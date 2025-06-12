import httpx
import streamlit as st

# Macros
BASE_URL = "http://127.0.0.1"
HOST_PORT = "8002"
ENDPOINT = f"{BASE_URL}:{HOST_PORT}/process_text"

# Page configuration
st.set_page_config(page_title="Socratic Agent UI", page_icon="🧠", layout="centered")
st.title("🧠 Socratic Agent Interface")
st.markdown(
    """
    Enter or upload text, select an operation, and let the Socratic Agent retrieve context and query the LLM for you.
    'Evaluation' elicits a critique based on the retrieved context. 'Summarization' prompts a survey of context
    information relevant to the text.
    """
)

# Session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "prompt_style" not in st.session_state:
    st.session_state.prompt_style = "evaluation"  # default

# Persistent storage for batches of retrieved documents
if "doc_batches" not in st.session_state:
    # Each batch is a dict: {"prompt_excerpt": str, "docs": list[str]}
    st.session_state.doc_batches = []

# Track the latest user prompt (used for sidebar header)
if "latest_prompt" not in st.session_state:
    st.session_state.latest_prompt = ""

# Prompt-style selector
st.selectbox(
    "Operation (applies to subsequent messages)",
    options=["evaluation", "summarization"],
    index=0 if st.session_state.prompt_style == "evaluation" else 1,
    key="prompt_style",
    help="Choose how the agent will analyze your input."
)

# -----------------------------------------------------------------------------
# Render existing chat history
# -----------------------------------------------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -----------------------------------------------------------------------------
# Chat input for new user message
# -----------------------------------------------------------------------------

user_input = st.chat_input("Type your message and press Enter…")

if user_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # Placeholder for assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking…")

    # -------------------------------------------------------------------------
    # Backend call
    # -------------------------------------------------------------------------
    try:
        response = httpx.post(
            ENDPOINT,
            json={
                "target_text": user_input,
                "prompt_style": st.session_state.prompt_style,
            },
            timeout=120,
        )

        if response.status_code != 200:
            assistant_content = f"❌ Error: {response.status_code} - {response.text}"
        else:
            data = response.json()

            if data.get("error_message"):
                # Show a more user-friendly error message
                error_msg = data["error_message"]
                if "LLM service is temporarily overloaded" in error_msg:
                    assistant_content = "⚠️ The AI service is currently busy. Please try again in a few moments."
                elif "Rate limit exceeded" in error_msg:
                    assistant_content = "⚠️ We've hit our rate limit. Please wait a minute before trying again."
                else:
                    assistant_content = f"⚠️ {error_msg}"
            else:
                model_name = data.get("model_name", "unknown-model")  # Fallback to "Assistant" if no model name
                response_text = data.get("processed_text", "<no response>")
                assistant_content = f"**{model_name}** says:\n\n{response_text}"

            # Only add documents to sidebar if there was no error
            if not data.get("error_message") and data.get("retrieved_documents"):
                # Add a new batch for this query's results
                batch_entry = {
                    "prompt_excerpt": user_input[:30].strip(),
                    "docs": data["retrieved_documents"],
                }
                st.session_state.doc_batches.append(batch_entry)

    except httpx.TimeoutException:
        assistant_content = "❌ Request timed out. The server took too long to respond."
    except httpx.RequestError as e:
        assistant_content = f"❌ Connection error: {e}"
    except Exception as e:
        assistant_content = f"❌ Unexpected error: {e}"

    # Update assistant placeholder and add to history
    with st.chat_message("assistant"):
        st.markdown(assistant_content)

    st.session_state.messages.append({"role": "assistant", "content": assistant_content})

# -----------------------------------------------------------------------------
# Final Sidebar Rendering (runs every time at the end of the script)
# -----------------------------------------------------------------------------
st.sidebar.header("📄 Documents")
if not st.session_state.doc_batches:
    st.sidebar.markdown("_No documents retrieved yet._")
else:
    doc_counter = 0
    # Render each batch from the session state sequentially
    for batch in st.session_state.doc_batches:
        start_index = doc_counter + 1
        end_index = doc_counter + len(batch["docs"])
        section_header = f"Docs {start_index}-{end_index}: {batch['prompt_excerpt']}…"
        st.sidebar.subheader(section_header)

        for doc_text in batch["docs"]:
            doc_counter += 1
            with st.sidebar.expander(f"Document {doc_counter}"):
                # Ensure proper text encoding
                try:
                    # First try to decode as UTF-8
                    safe_text = doc_text.encode('utf-8').decode('utf-8')
                except UnicodeError:
                    try:
                        # If that fails, try latin-1
                        safe_text = doc_text.encode('latin-1').decode('utf-8')
                    except UnicodeError:
                        # If all else fails, use a more permissive approach
                        safe_text = doc_text.encode('latin-1', errors='replace').decode('utf-8', errors='replace')
                
                st.text(safe_text)  # Use st.text instead of st.write for better text handling

# -----------------------------------------------------------------------------
st.caption(f"Running against MCP Host at: {ENDPOINT}") 