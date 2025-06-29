import uvicorn
from fastapi import FastAPI

from socratic_agent.core.config import API_KEY
from socratic_agent.adk.prompt_templates import create_evaluation_prompt, create_summarization_prompt
from socratic_agent.adk.llm_interaction import get_llm_response
from socratic_agent.mcp_host.client import MCPClient, MCPClientError
from socratic_agent.mcp_host.models import HostInput, HostOutput

app = FastAPI(
    title="Socratic Agent - MCP Host",
    description="Orchestrates document retrieval via MCP Server and LLM interaction.",
    version="0.1.0"
)

HOST_URL = "http://127.0.0.1"
PORT = 8002
EXPECTED_RETRIEVER_TOOL_NAME = "document_retriever"
if not API_KEY:
    raise ValueError("MCP Host: GOOGLE_API_KEY not configured. Cannot call LLM.")

@app.post("/process_text", response_model=HostOutput)
async def process_text_endpoint(host_input: HostInput):
    """
    Receives target text, retrieves relevant documents via MCP Server, 
    constructs a prompt, calls an LLM, and returns the response.
    """
    print(f"MCP Host: Processing text: {host_input.target_text[:min(len(host_input.target_text), 100)]}...")
    
    mcp_client = MCPClient() 
    if host_input is None or not hasattr(host_input, "target_text") or not hasattr(host_input, "prompt_style"):
        raise ValueError("MCP Host: HostInput is None or missing target_text attribute.")
    if host_input.prompt_style not in ["evaluation", "summarization"]:
        raise ValueError("MCP Host: Unsupported prompt style.")

    retrieved_documents = []
    try:
        # Get tool registry from MCP Server
        print("MCP Host: Getting tool registry from MCP Server...")
        tools_info = await mcp_client.get_available_tools()
        if not any(tool.tool_name == EXPECTED_RETRIEVER_TOOL_NAME for tool in tools_info.tools):
            llm_error = f"MCP Host: Document retriever tool '{EXPECTED_RETRIEVER_TOOL_NAME}' not found."
            print(llm_error)
            return HostOutput(processed_text="", error_message=llm_error)

        # Step 2: Retrieve documents using the tool
        print("MCP Host: Retrieving documents using the tool...")
        tool_invocation_response = await mcp_client.retrieve_documents(
            tool_name=EXPECTED_RETRIEVER_TOOL_NAME, 
            query_text=host_input.target_text, 
            k=5
        )
        retriever_tool_output = tool_invocation_response.get("results", {})
        retrieved_documents = retriever_tool_output.get("retrieved_documents", [])
        if not retrieved_documents:
            raise RuntimeError("Tool invocation succeeded but returned no documents.")
        
        retrieved_documents = [document.get('text') for document in retrieved_documents]
        
    except MCPClientError as e:
        error_message = f"Failed to retrieve documents: {str(e)}"
        print(error_message)
        return HostOutput(
            processed_text="", 
            error_message=error_message, 
            retrieved_documents=[]
        )
    
    except Exception as e:
        error_message = f"Unexpected error during document retrieval: {str(e)}"
        print(error_message)
        return HostOutput(
            processed_text="", 
            error_message=error_message, 
            retrieved_documents=[]
        )

    finally:
        await mcp_client.close()

    try:
        # Generate prompt
        print("MCP Host: Generating prompt...")
        prompt_text = None
        if host_input.prompt_style == "evaluation":
            prompt_text = create_evaluation_prompt(user_prompt=host_input.target_text, retrieved_docs=retrieved_documents)
        elif host_input.prompt_style == "summarization":
            prompt_text = create_summarization_prompt(user_prompt=host_input.target_text, retrieved_docs=retrieved_documents)
        
        # LLM call
        print("MCP Host: Calling LLM...")
        llm_response_text, model_name = await get_llm_response(prompt_text)
        
        return HostOutput(
            processed_text=llm_response_text,
            retrieved_documents=retrieved_documents,
            prompt_used=prompt_text,
            error_message=None,
            model_name=model_name
        )
        
    except RuntimeError as e:
        # Handle LLM-specific errors
        error_message = str(e)
        print(error_message)
        return HostOutput(
            processed_text="",
            retrieved_documents=retrieved_documents,
            prompt_used=prompt_text,
            error_message=error_message,
            model_name=None
        )
        
    except Exception as e:
        error_message = f"Unexpected error during LLM processing: {str(e)}"
        print(error_message)
        return HostOutput(
            processed_text="",
            retrieved_documents=retrieved_documents,
            prompt_used=prompt_text,
            error_message=error_message,
            model_name=None
        )

if __name__ == "__main__":
    print(f"Attempting to run MCP Host with Uvicorn on {HOST_URL}:{PORT}")
    print("Endpoints available:")
    print("  POST /process_text")
    print("  GET  /docs (Swagger UI)")
    print("  GET  /redoc (ReDoc UI)")
    uvicorn.run(app, host=HOST_URL, port=PORT) 