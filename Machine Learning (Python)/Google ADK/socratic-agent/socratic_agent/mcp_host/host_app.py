from fastapi import FastAPI, HTTPException
from typing import Optional, List, Dict, Any

from socratic_agent.core.config import API_KEY # For LLM interaction
from socratic_agent.adk.prompt_templates import create_evaluation_prompt, create_summarization_prompt # Import new prompt functions
from socratic_agent.core.llm_interaction import get_llm_response
# Import the new SimpleMCPClient
from .client import SimpleMCPClient 
# DOCUMENT_RETRIEVER_TOOL_NAME will now be fetched dynamically
from .models import HostInput, HostOutput, MCPToolInfo # MCPToolRegistryInfo if needed for polling

app = FastAPI(
    title="Socratic Agent - MCP Host",
    description="Orchestrates document retrieval via MCP Server and LLM interaction.",
    version="0.1.0"
)

# Define the expected name for the retriever tool for robust lookup
# This matches the name in socratic_agent/mcp_server/server_app.py
EXPECTED_RETRIEVER_TOOL_NAME = "document_retriever"

@app.post("/process_text", response_model=HostOutput)
async def process_text_endpoint(
    host_input: HostInput
):
    """
    Receives target text, retrieves relevant documents via MCP Server, 
    constructs a prompt, calls an LLM, and returns the response.
    """
    target_text = host_input.target_text
    retrieved_docs_payload: Optional[List[Dict[str, Any]]] = None
    prompt_text: Optional[str] = None
    llm_error: Optional[str] = None
    retrieval_response: Optional[Dict[str, Any]] = None

    mcp_client = SimpleMCPClient() # Instantiate the client
    actual_retriever_tool_name: Optional[str] = None

    try:
        # 1. Poll MCP Server for tools and find the document retriever
        print(f"MCP Host: Polling MCP Server for available tools...")
        tools_info = await mcp_client.get_available_tools()

        if not tools_info or not tools_info.tools:
            llm_error = "MCP Host: No tools reported by MCP Server."
            print(llm_error)
            # Early exit if no tools are available
            return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])
        
        found_tool = False
        for tool in tools_info.tools:
            if tool.tool_name == EXPECTED_RETRIEVER_TOOL_NAME:
                actual_retriever_tool_name = tool.tool_name
                found_tool = True
                print(f"MCP Host: Found document retriever tool: '{actual_retriever_tool_name}'")
                break
        
        if not found_tool:
            llm_error = f"MCP Host: Document retriever tool '{EXPECTED_RETRIEVER_TOOL_NAME}' not found on MCP Server."
            print(llm_error)
            # Early exit if the specific tool is not available
            return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])

        # 2. Use MCP Server's tool (top-k document retrieval)
        print(f"MCP Host: Received target text: '{target_text[:50]}...'")
        print(f"MCP Host: Invoking '{actual_retriever_tool_name}' tool on MCP Server...")
        
        retrieval_response = await mcp_client.retrieve_documents(
            tool_name=actual_retriever_tool_name, 
            query_text=target_text, 
            k=5 # k=5 as per project.md
        )

        if retrieval_response and retrieval_response.get("results"):
            retrieved_docs_data = retrieval_response["results"].get("retrieved_documents")
            if isinstance(retrieved_docs_data, list):
                retrieved_docs_payload = retrieved_docs_data
                print(f"MCP Host: Retrieved {len(retrieved_docs_payload)} documents from MCP Server.")
            else:
                print(f"MCP Host: Warning - 'retrieved_documents' from server was not a list or was missing. Payload: {retrieved_docs_data}")
                llm_error = "Failed to properly parse retrieved documents from MCP Server."
                retrieved_docs_payload = [] 
        elif retrieval_response and retrieval_response.get("error"):
            error_msg = retrieval_response["error"]
            print(f"MCP Host: Error from MCP Server tool invocation: {error_msg}")
            llm_error = f"MCP Server tool error: {error_msg}"
        else:
            print("MCP Host: Failed to invoke tool or unexpected response from MCP Server.")
            llm_error = "Failed to retrieve documents from MCP Server."
            
    except Exception as e:
        # Catch any other exceptions during client interaction
        print(f"MCP Host: Exception during MCP client interaction: {type(e).__name__} - {e}")
        llm_error = f"MCP client communication error: {e}"
    finally:
        await mcp_client.close() # Ensure client is closed

    # If a critical error occurred during retrieval, return early
    if llm_error and not retrieved_docs_payload:
        return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])

    if retrieved_docs_payload is None: retrieved_docs_payload = []

    # 3. Prepare the prompt
    print("MCP Host: Constructing prompt...")
    prompt_style = "evaluation" 
    doc_texts_for_prompt: List[str] = []
    if retrieved_docs_payload:
        for doc in retrieved_docs_payload:
            text_content = doc.get('text', doc.get('document'))
            if text_content:
                doc_texts_for_prompt.append(str(text_content))
            else:
                print(f"MCP Host: Warning - Document with ID {doc.get('id', 'Unknown')} missing 'text' or 'document' field.")

    if prompt_style == "evaluation":
        prompt_text = create_evaluation_prompt(user_prompt=target_text, retrieved_docs=doc_texts_for_prompt)
    elif prompt_style == "summarization":
        prompt_text = create_summarization_prompt(retrieved_docs=doc_texts_for_prompt, user_prompt=target_text)
    else:
        error_for_prompt_style = f"Unsupported prompt style: {prompt_style}"
        if llm_error: # Append to existing error if any
            llm_error += f"; {error_for_prompt_style}"
        else:
            llm_error = error_for_prompt_style
        prompt_text = f"Target Text: {target_text}\\n\\nDocuments: {doc_texts_for_prompt}" 
        print(f"MCP Host: Error - {error_for_prompt_style}. Using basic prompt.")

    print(f"MCP Host: Prompt constructed (style: {prompt_style}). Length: {len(prompt_text)}")

    # 4. Call the LLM with the prompt
    if not API_KEY:
        print("MCP Host: GOOGLE_API_KEY not configured. Cannot call LLM.")
        return HostOutput(
            processed_text="", 
            retrieved_documents=retrieved_docs_payload, 
            prompt_used=prompt_text, 
            error_message="LLM API Key not configured."
        )
    
    print("MCP Host: Calling LLM...")
    llm_response_text = await get_llm_response(prompt_text)
    
    if llm_response_text.startswith("Error generating LLM response:") or \
       llm_response_text.startswith("LLM client not configured") or \
       llm_response_text.startswith("LLM response was empty or blocked") or \
       (llm_error and not llm_response_text and not retrieved_docs_payload): 
        final_error_message = llm_response_text if not llm_response_text.startswith("Error") else (llm_error or "") + "; " + llm_response_text
        return HostOutput(
            processed_text="", 
            retrieved_documents=retrieved_docs_payload, 
            prompt_used=prompt_text, 
            error_message=final_error_message
        )

    print("MCP Host: LLM call successful.")
    return HostOutput(
        processed_text=llm_response_text,
        retrieved_documents=retrieved_docs_payload,
        prompt_used=prompt_text,
        error_message=llm_error
    )

if __name__ == "__main__":
    import uvicorn
    print("Attempting to run MCP Host with Uvicorn on http://127.0.0.1:8002")
    print("Endpoints available:")
    print("  POST /process_text")
    print("  GET  /docs (Swagger UI)")
    print("  GET  /redoc (ReDoc UI)")
    uvicorn.run(app, host="127.0.0.1", port=8002) 