import httpx
from typing import Any, Dict, List, Optional

from socratic_agent.core.config import MCP_SERVER_URL
# Using models defined in the host's own model file
from .models import MCPToolRegistryInfo, MCPToolInfo

class SimpleMCPClient:
    """A simple client to interact with the MCP Server without managed lifespan."""
    def __init__(self, server_url: str = MCP_SERVER_URL):
        self._server_url = server_url
        # Initialize httpx.AsyncClient here; it will be closed manually after use
        self._client = httpx.AsyncClient(base_url=self._server_url)

    async def get_available_tools(self) -> Optional[MCPToolRegistryInfo]:
        """Polls the MCP server for its tool registry."""
        try:
            response = await self._client.get("/tools")
            response.raise_for_status()
            tool_data = response.json()
            return MCPToolRegistryInfo(**tool_data)
        except httpx.RequestError as e:
            print(f"MCPClient: Error connecting to MCP server at {self._server_url}/tools: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"MCPClient: Server returned error for /tools: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"MCPClient: Unexpected error when fetching tools: {e}")
            return None

    async def invoke_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Invokes a tool on the MCP server."""
        request_payload = {"parameters": parameters}
        try:
            response = await self._client.post(
                f"/tools/{tool_name}/invoke", 
                json=request_payload
            )
            response.raise_for_status()
            return response.json() # Expected: {"results": ..., "error": ...}
        except httpx.RequestError as e:
            print(f"MCPClient: Error connecting to MCP server at /tools/{tool_name}/invoke: {e}")
            return {"results": {}, "error": str(e)}
        except httpx.HTTPStatusError as e:
            print(f"MCPClient: Server returned error for /tools/{tool_name}/invoke: {e.response.status_code} - {e.response.text}")
            return {"results": {}, "error": f"{e.response.status_code} - {e.response.text}"}
        except Exception as e:
            print(f"MCPClient: Unexpected error when invoking tool {tool_name}: {e}")
            return {"results": {}, "error": str(e)}

    async def retrieve_documents(self, tool_name: str, query_text: str, k: int = 5) -> Optional[Dict[str, Any]]:
        """Specific method to invoke a document retriever tool by its identified name."""
        params = {"query_text": query_text, "k": k}
        return await self.invoke_tool(tool_name, params)

    async def close(self):
        """Closes the httpx client."""
        await self._client.aclose() 