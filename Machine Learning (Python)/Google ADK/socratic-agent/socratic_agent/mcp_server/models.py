from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

# --- Tool-Specific Schemas (Examples for a Retriever Tool) ---
class RetrieverToolInputSchema(BaseModel):
    """Input schema specifically for the document retriever tool."""
    query_text: str = Field(..., description="The text to search for.")
    k: int = Field(default=5, gt=0, le=100, description="Number of top documents to retrieve (1-100).")

class RetrieverToolOutputSchema(BaseModel):
    """Output schema specifically for the document retriever tool."""
    retrieved_documents: List[Dict[str, Any]] = Field(..., description="List of retrieved document objects, including text and metadata.")
    error: Optional[str] = None


# --- Generic MCP Models ---
class ToolDefinition(BaseModel):
    """Standard MCP model for defining a tool."""
    tool_name: str = Field(..., description="Unique name of the tool.", examples=["document_retriever"])
    description: str = Field(..., description="Description of what the tool does.")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for the tool's input, generated from a Pydantic model.")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema for the tool's output, generated from a Pydantic model.")

class ToolRegistry(BaseModel):
    """A list of all tools provided by an MCP Server."""
    tools: List[ToolDefinition]


# --- Tool Invocation Models (MCP Host -> MCP Server) ---
class ToolInvocationInput(BaseModel):
    """Input for invoking a specific tool on the MCP Server."""
    parameters: Dict[str, Any] = Field(..., description="Parameters for the tool, matching its input_schema.")

class ToolInvocationResponse(BaseModel):
    """Response from an MCP Server after invoking a tool."""
    results: Dict[str, Any] = Field(..., description="Results from the tool, matching its output_schema.")
    error: Optional[str] = None


# --- General Request/Response Models (MCP Client -> MCP Host) ---
class SocraticRequest(BaseModel):
    """Request from a client to the Socratic agent (MCP Host)."""
    target_text: str = Field(..., description="The user's input text/query/prompt.")
    requested_operation: Literal["summarize", "evaluate"] = Field(..., description="The operation to perform ('summarize' or 'evaluate').")

class SocraticResponse(BaseModel):
    """Response from the Socratic agent (MCP Host) to a client."""
    llm_response: str = Field(..., description="The final processed response from the LLM.")
    retrieved_context: Optional[List[str]] = Field(default=None, description="Documents retrieved and used as context.")
    error: Optional[str] = None


if __name__ == '__main__':
    print("Testing MCP Models...")

    retriever_input = RetrieverToolInputSchema(query_text="test query", k=3)
    assert retriever_input.query_text == "test query", f"Expected 'test query', got {retriever_input.query_text}"
    assert retriever_input.k == 3, f"Expected 3, got {retriever_input.k}"
    print("RetrieverToolInputSchema valid test: PASSED")
    
    retriever_output = RetrieverToolOutputSchema(retrieved_documents=["doc1"])
    assert retriever_output.retrieved_documents == ["doc1"], f"Expected ['doc1'], got {retriever_output.retrieved_documents}"
    print("RetrieverToolOutputSchema valid test: PASSED")

    retrieval_tool_def = ToolDefinition(
        tool_name="document_retriever",
        description="Retrieves relevant documents from the knowledge base.",
        input_schema=RetrieverToolInputSchema.model_json_schema(),
        output_schema=RetrieverToolOutputSchema.model_json_schema()
    )
    assert retrieval_tool_def.tool_name == "document_retriever"
    assert "query_text" in retrieval_tool_def.input_schema.get("properties", {})
    assert "retrieved_documents" in retrieval_tool_def.output_schema.get("properties", {})
    print("ToolDefinition test (with specific schemas): PASSED")

    invocation_input = ToolInvocationInput(parameters={"query_text": "What is AI?", "k": 5})
    assert invocation_input.parameters["query_text"] == "What is AI?"
    print("ToolInvocationInput test: PASSED")

    s_request_summarize = SocraticRequest(target_text="User's deep question.", requested_operation="summarize")
    assert s_request_summarize.target_text == "User's deep question."
    assert s_request_summarize.requested_operation == "summarize"

    s_request_evaluate = SocraticRequest(target_text="Another question.", requested_operation="evaluate")
    assert s_request_evaluate.requested_operation == "evaluate"
    print("SocraticRequest with Literal test: PASSED")

    # Test invalid operation for SocraticRequest (Pydantic should raise ValidationError)
    invalid_op_passed = False
    try:
        SocraticRequest(target_text="Bad op.", requested_operation="delete")
    except Exception:
        invalid_op_passed = True
    assert invalid_op_passed, "SocraticRequest did not raise error for invalid 'requested_operation'"
    print("SocraticRequest invalid operation test: PASSED")

    s_response = SocraticResponse(llm_response="A thoughtful answer.", retrieved_context=["doc X"])
    assert s_response.llm_response == "A thoughtful answer."
    assert s_response.retrieved_context == ["doc X"]
    print("SocraticResponse test: PASSED")

    print("MCP Models tests completed.") 