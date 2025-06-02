from fastapi import FastAPI, HTTPException
from pydantic import ValidationError # Import ValidationError
from typing import List

# Import models from our mcp_server.models module
from .models import (
    ToolDefinition, ToolRegistry, 
    RetrieverToolInputSchema, RetrieverToolOutputSchema, # Using specific schema names
    ToolInvocationInput, ToolInvocationResponse
)

# Import ChromaDB interaction utilities from the rag module
from socratic_agent.rag.embedding_utils import get_embedding_client, get_or_create_collection
from socratic_agent.rag.retrieval_utils import get_top_k
from socratic_agent.core.config import API_KEY # To pass to collection creation if needed

app = FastAPI(
    title="Socratic Agent - MCP Server",
    description="Exposes tools like document retrieval to an MCP Host.",
    version="0.1.0"
)

# --- Globals for ChromaDB (initialize on startup or first request) ---
# In a real app, consider FastAPI's lifespan events for setup/teardown
chroma_client = None
document_collection = None

def initialize_chroma():
    """Initializes ChromaDB client and collection if not already done."""
    global chroma_client, document_collection
    if chroma_client is None:
        print("Initializing ChromaDB client for MCP Server...")
        chroma_client = get_embedding_client()
        assert chroma_client is not None, "ChromaDB client initialization failed."
    if document_collection is None:
        print("Getting/creating ChromaDB collection for MCP Server...")
        document_collection = get_or_create_collection(chroma_client, api_key=API_KEY)
        assert document_collection is not None, "Document collection initialization failed."
        print(f"MCP Server connected to collection: {document_collection.name} with {document_collection.count()} items.")

initialize_chroma()

# --- Tool Definitions --- 
# This would typically be more dynamic or configured elsewhere
DOCUMENT_RETRIEVER_TOOL_NAME = "document_retriever"
document_retriever_tool = ToolDefinition(
    tool_name=DOCUMENT_RETRIEVER_TOOL_NAME,
    description="Retrieves top-k relevant document snippets from the knowledge base based on a query text.",
    input_schema=RetrieverToolInputSchema.model_json_schema(),
    output_schema=RetrieverToolOutputSchema.model_json_schema()
)
TOOL_REGISTRY = ToolRegistry(tools=[document_retriever_tool])


# --- API Endpoints ---
@app.get("/tools", response_model=ToolRegistry)
async def list_tools():
    """Lists all tools available from this MCP Server."""
    print("MCP Server: /tools endpoint called.")
    return TOOL_REGISTRY

@app.post(f"/tools/{{tool_name}}/invoke", response_model=ToolInvocationResponse)
async def invoke_tool(tool_name: str, invocation_input: ToolInvocationInput):
    """Invokes a specified tool with the given input parameters."""
    print(f"MCP Server: /tools/{tool_name}/invoke endpoint called with input: {invocation_input.parameters}")
    
    if tool_name not in [tool.tool_name for tool in TOOL_REGISTRY.tools]:
        print(f"Error: Tool '{tool_name}' not found.")
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    if tool_name == DOCUMENT_RETRIEVER_TOOL_NAME:
        if not document_collection:
            initialize_chroma() # Attempt re-initialization if collection is somehow None
            if not document_collection:
                print("Error: Document collection is not available.")
                raise HTTPException(status_code=503, detail="Document collection (ChromaDB) is not available.")
        try:
            # Validate parameters against the specific ToolInputSchema for the retriever
            retriever_params = RetrieverToolInputSchema(**invocation_input.parameters)
            retrieved_docs_list = get_top_k(
                collection=document_collection,
                target_text=retriever_params.query_text,
                k=retriever_params.k
            )
            output_data = RetrieverToolOutputSchema(retrieved_documents=retrieved_docs_list)
            print(f"Retrieved {len(retrieved_docs_list)} documents for query: '{retriever_params.query_text}'")
            return ToolInvocationResponse(results=output_data.model_dump(), error=None)
        
        except ValidationError as ve:
            error_message = f"Input validation error for '{DOCUMENT_RETRIEVER_TOOL_NAME}': {ve.errors()}"
            print(error_message)
            # Return 422 for Pydantic validation errors
            # Optionally, can format ve.errors() for a cleaner detail message
            return ToolInvocationResponse(results={}, error=error_message) # Return 200 with error in payload
            # OR raise HTTPException(status_code=422, detail=ve.errors())
        
        except HTTPException as http_exc:
            raise http_exc # Re-raise already formed HTTP exceptions
        
        except Exception as e:
            error_message = f"Unexpected error invoking '{DOCUMENT_RETRIEVER_TOOL_NAME}': {type(e).__name__} - {e}"
            print(error_message)
            # For other unexpected errors during tool execution
            return ToolInvocationResponse(results={}, error=error_message) # Return 200 with error in payload
            # OR raise HTTPException(status_code=500, detail=error_message)
    else:
        # This case should ideally not be reached if tool_name check passes
        print(f"Error: Invocation logic for tool '{tool_name}' not implemented.")
        raise HTTPException(status_code=501, detail=f"Invocation logic for tool '{tool_name}' not implemented")


if __name__ == "__main__":
    # This block is for running the FastAPI app directly with Uvicorn for testing.
    # To run from CLI: uvicorn socratic_agent.mcp_server.server_app:app --reload --port 8001
    import uvicorn
    print("Attempting to run MCP Server with Uvicorn on http://127.0.0.1:8001")
    print("Endpoints available:")
    print("  GET  /docs (Swagger UI)")
    print("  GET  /redoc (ReDoc UI)")
    print("  GET  /tools")
    print(f"  POST /tools/{DOCUMENT_RETRIEVER_TOOL_NAME}/invoke")
    
    # Ensure Chroma is initialized before starting server if __main__ is run
    if not document_collection:
        print("Initializing ChromaDB from __main__ before starting server...")
        initialize_chroma()
        if not document_collection:
            print("CRITICAL: ChromaDB collection could not be initialized. Server might not work correctly.")

    uvicorn.run(app, host="127.0.0.1", port=8001) 