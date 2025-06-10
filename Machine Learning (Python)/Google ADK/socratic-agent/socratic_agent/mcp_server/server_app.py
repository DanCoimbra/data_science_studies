import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from .models import (
    ToolDefinition, ToolRegistry, 
    RetrieverToolInputSchema, RetrieverToolOutputSchema,
    ToolInvocationInput, ToolInvocationResponse
)
from socratic_agent.rag.embedding_utils import get_embedding_client, get_or_create_collection
from socratic_agent.rag.retrieval_utils import get_top_k
from socratic_agent.core.config import API_KEY

HOST_URL = "http://127.0.0.1"
PORT = 8001

app = FastAPI(
    title="Socratic Agent - MCP Server",
    description="Exposes tools like document retrieval to an MCP Host.",
    version="0.1.0"
)


def initialize_chroma():
    """Initializes ChromaDB client and collection if not already done."""

    global chroma_client, document_collection
    
    if chroma_client is None:
        try:
            chroma_client = get_embedding_client()
        except Exception as e:
            raise RuntimeError(f"ChromaDB client initialization failed: {e}")

    if document_collection is None:
        try:
            document_collection = get_or_create_collection(chroma_client)
        except Exception as e:
            raise RuntimeError(f"Document collection initialization failed: {e}")

chroma_client = None
document_collection = None
initialize_chroma()
print(f"MCP Server: ChromaDB client and collection initialized.")

# Defines tool registry
DOCUMENT_RETRIEVER_TOOL_NAME = "document_retriever"
document_retriever_tool = ToolDefinition(
    tool_name=DOCUMENT_RETRIEVER_TOOL_NAME,
    description="Retrieves top-k relevant document snippets from the knowledge base based on a query text.",
    input_schema=RetrieverToolInputSchema.model_json_schema(),
    output_schema=RetrieverToolOutputSchema.model_json_schema()
)
TOOL_REGISTRY = ToolRegistry(tools=[document_retriever_tool])


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
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    if tool_name == DOCUMENT_RETRIEVER_TOOL_NAME:
        try:
            retriever_params = RetrieverToolInputSchema(**invocation_input.parameters)
            retrieved_documents = get_top_k(
                collection=document_collection,
                target_text=retriever_params.query_text,
                k=retriever_params.k
            )
            output_data = RetrieverToolOutputSchema(retrieved_documents=retrieved_documents)
            return ToolInvocationResponse(results=output_data.model_dump(), error=None)
        
        except ValidationError as ve:
            error_message = f"Input validation error for '{DOCUMENT_RETRIEVER_TOOL_NAME}': {ve.errors()}"
            return ToolInvocationResponse(results={}, error=error_message)
        
        except HTTPException as http_exc:
            raise http_exc
        
        except Exception as e:
            error_message = f"Unexpected error invoking '{DOCUMENT_RETRIEVER_TOOL_NAME}': {type(e).__name__} - {e}"
            return ToolInvocationResponse(results={}, error=error_message)
    else:
        raise HTTPException(status_code=501, detail=f"Invocation logic for tool '{tool_name}' not implemented")


if __name__ == "__main__":
    print(f"Attempting to run MCP Server with Uvicorn on {HOST_URL}:{PORT}")
    print("Endpoints available:")
    print("  GET  /docs (Swagger UI)")
    print("  GET  /redoc (ReDoc UI)")
    print("  GET  /tools")
    print(f"  POST /tools/{DOCUMENT_RETRIEVER_TOOL_NAME}/invoke")
    uvicorn.run(app, host=HOST_URL, port=PORT) 