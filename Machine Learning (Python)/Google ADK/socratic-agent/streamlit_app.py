import os
import httpx
import streamlit as st

BASE_URL = "http://127.0.0.1"
HOST_PORT = "8002"
ENDPOINT = f"{BASE_URL}:{HOST_PORT}/process_text"

st.set_page_config(page_title="Socratic Agent UI", page_icon="🧠", layout="centered")

st.title("🧠 Socratic Agent Interface")
st.markdown(
    """
    Enter or upload text, select an operation, and let the Socratic Agent retrieve context and query the LLM for you.
    'Evaluation' elicits a critique based on the retrieved context. 'Summarization' prompts a survey of context
    information relevant to the text.
    """
)

# --- Input Section ---------------------------------------------------------
text_input = st.text_area("Target text", "", height=200, placeholder="Paste or type text here…")

uploaded_file = st.file_uploader("…or upload a .txt file", type=["txt"], label_visibility="collapsed")
if uploaded_file is not None:
    try:
        file_contents = uploaded_file.read().decode("utf-8", errors="ignore")
        text_input = file_contents
        st.success("File loaded into text area. You can edit before submitting.")
    except Exception as e:
        st.error(f"Could not read file: {e}")

prompt_style = st.radio("Operation", options=["evaluation", "summarization"], horizontal=True)

submit_clicked = st.button("Send to Socratic Agent")

# --- Submission / Response -------------------------------------------------
if submit_clicked:
    if not text_input.strip():
        st.warning("Please provide text to process.")
    else:
        with st.spinner("Contacting MCP Host…"):
            try:
                response = httpx.post(
                    ENDPOINT,
                    json={"target_text": text_input, "prompt_style": prompt_style},
                    timeout=60
                )

                if response.status_code != 200:
                    st.error(f"MCP Host returned {response.status_code}: {response.text}")
                else:
                    data = response.json()

                    if data.get("error_message"):
                        st.error(data["error_message"])

                    st.subheader("LLM Response")
                    st.write(data.get("processed_text", "<no response>"))

                    docs = data.get("retrieved_documents") or []
                    if docs:
                        with st.expander(f"Retrieved Documents ({len(docs)})"):
                            for idx, doc in enumerate(docs, start=1):
                                st.markdown(f"**Document {idx}**")
                                st.write(doc)

            except httpx.RequestError as e:
                st.error(f"Connection error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

st.caption("Running against MCP Host at: " + ENDPOINT) 