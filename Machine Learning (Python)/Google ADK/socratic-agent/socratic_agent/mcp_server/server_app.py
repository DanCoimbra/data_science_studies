from contextlib import asynccontextmanager
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

# Globals to be populated by the lifespan manager
CHROMA_CLIENT = None
CHROMA_COLLECTION = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI app.
    Initializes ChromaDB on startup.
    """
    global CHROMA_CLIENT, CHROMA_COLLECTION
    print("MCP Server: Lifespan startup...")
    
    # Fail fast if critical services cannot be initialized.
    CHROMA_CLIENT = get_embedding_client()
    if CHROMA_CLIENT is None:
        raise RuntimeError("ChromaDB client initialization failed.")
    
    CHROMA_COLLECTION = get_or_create_collection(CHROMA_CLIENT)
    if CHROMA_COLLECTION is None:
        raise RuntimeError("Document collection initialization failed.")
    
    print(f"MCP Server: ChromaDB client and collection '{CHROMA_COLLECTION.name}' initialized successfully.")
    
    yield
    
    print("MCP Server: Lifespan shutdown.")
    CHROMA_CLIENT, CHROMA_COLLECTION = None, None


app = FastAPI(
    title="Socratic Agent - MCP Server",
    description="Exposes tools like document retrieval to an MCP Host.",
    version="0.1.0",
    lifespan=lifespan
)

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
            # Add a check to ensure the collection was initialized successfully
            if CHROMA_COLLECTION is None:
                raise HTTPException(status_code=503, detail="ChromaDB service is unavailable due to a startup error.")

            retriever_params = RetrieverToolInputSchema(**invocation_input.parameters)
            retrieved_documents = get_top_k(
                collection=CHROMA_COLLECTION,
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