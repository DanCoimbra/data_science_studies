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
    mcp_client = MCPClient()
    if host_input is None or not host_input.hasattr("target_text") or not host_input.hasattr("prompt_style"):
        raise ValueError("MCP Host: HostInput is None or missing target_text attribute.")
    if host_input.prompt_style not in ["evaluation", "summarization"]:
        raise ValueError("MCP Host: Unsupported prompt style.")

    try:
        # Get tool registry from MCP Server
        tools_info = await mcp_client.get_available_tools()

        if not tools_info or not tools_info.tools:
            llm_error = "MCP Host: No tools reported by MCP Server."
            return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])
        
        for tool in tools_info.tools:
            if tool.tool_name == EXPECTED_RETRIEVER_TOOL_NAME:
                break
        else:
            llm_error = f"MCP Host: Document retriever tool '{EXPECTED_RETRIEVER_TOOL_NAME}' not found on MCP Server."
            return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])
        
        # Get documents from MCP Server
        tool_invocation_response = await mcp_client.retrieve_documents(
            tool_name=EXPECTED_RETRIEVER_TOOL_NAME, 
            query_text=host_input.target_text, 
            k=5
        )
        retriever_tool_output = tool_invocation_response.get("results", {})
        retrieved_documents = retriever_tool_output.get("retrieved_documents", [])
        if not retrieved_documents:
            llm_error = "MCP Host: Tool invocation succeeded but returned no documents."
            return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])
        else:
            retrieved_documents = [document.get('text') for document in retrieved_documents]
        
    except MCPClientError as e:
        llm_error = f"MCP client communication error: {e}"
        return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])
    
    except Exception as e:
        llm_error = f"MCP Host: Unexpected error: {e}"
        return HostOutput(processed_text="", error_message=llm_error, retrieved_documents=[])

    finally:
        await mcp_client.close()

    # Generate prompt
    prompt_text = None
    if host_input.prompt_style == "evaluation":
        prompt_text = create_evaluation_prompt(user_prompt=host_input.target_text, retrieved_docs=retrieved_documents)
    elif host_input.prompt_style == "summarization":
        prompt_text = create_summarization_prompt(user_prompt=host_input.target_text, retrieved_docs=retrieved_documents)
    
    # LLM call
    llm_response_text = await get_llm_response(prompt_text)
    return HostOutput(
        processed_text=llm_response_text,
        retrieved_documents=retrieved_documents,
        prompt_used=prompt_text,
        error_message=None
    )

if __name__ == "__main__":
    print(f"Attempting to run MCP Host with Uvicorn on {HOST_URL}:{PORT}")
    print("Endpoints available:")
    print("  POST /process_text")
    print("  GET  /docs (Swagger UI)")
    print("  GET  /redoc (ReDoc UI)")
    uvicorn.run(app, host=HOST_URL, port=PORT) 