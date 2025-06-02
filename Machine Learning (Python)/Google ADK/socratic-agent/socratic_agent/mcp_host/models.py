from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class HostInput(BaseModel):
    target_text: str = Field(..., description="The target text to be analyzed or processed.")
    # Potentially other parameters like user_id, session_id, etc. in the future

class HostOutput(BaseModel):
    processed_text: str = Field(..., description="The final processed text or response from the LLM.")
    retrieved_documents: Optional[List[Dict[str, Any]]] = Field(None, description="Documents retrieved by the MCP server, if any.")
    prompt_used: Optional[str] = Field(None, description="The actual prompt sent to the LLM.")
    error_message: Optional[str] = Field(None, description="Any error message if processing failed.")

# Example of how MCP Tool models might be represented if the host needs to understand them deeply.
# For now, we'll assume the host gets tool info as dicts from the server.
class MCPToolInfo(BaseModel):
    tool_name: str
    description: str
    input_schema: Dict[str, Any] # JSON schema as dict
    output_schema: Dict[str, Any] # JSON schema as dict

class MCPToolRegistryInfo(BaseModel):
    tools: List[MCPToolInfo] 