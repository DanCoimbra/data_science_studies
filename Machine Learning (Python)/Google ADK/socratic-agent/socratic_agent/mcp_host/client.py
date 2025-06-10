import httpx
from typing import Any, Dict

from socratic_agent.core.config import MCP_SERVER_URL
from .models import MCPToolRegistryInfo


class MCPClientError(Exception):
    """Custom exception for all MCP client-related errors."""
    pass


class MCPClient:
    """A simple, non-managed client to interact with the MCP Server."""
    def __init__(self, server_url: str = MCP_SERVER_URL):
        if not server_url:
            raise ValueError("MCP_SERVER_URL cannot be empty.")
        self._server_url = server_url
        self._client = httpx.AsyncClient(base_url=self._server_url)

    async def get_available_tools(self) -> MCPToolRegistryInfo:
        """
        Polls the MCP server for its tool registry.
        Raises MCPClientError on any failure.
        """
        print(f"MCP Client: Polling MCP Server for available tools...")
        try:
            response = await self._client.get("/tools")
            response.raise_for_status()
            return MCPToolRegistryInfo(**response.json())
        except httpx.RequestError as e:
            raise MCPClientError(f"Network error getting tools: {e}") from e
        except httpx.HTTPStatusError as e:
            raise MCPClientError(f"Server error getting tools: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            raise MCPClientError(f"Unexpected error getting tools: {e}") from e

    async def invoke_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invokes a tool on the MCP server.
        Raises MCPClientError on any failure.
        """
        print(f"MCP Client: Invoking tool '{tool_name}' with parameters: {parameters}")
        request_payload = {"parameters": parameters}
        try:
            response = await self._client.post(
                f"/tools/{tool_name}/invoke", 
                json=request_payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise MCPClientError(f"Network error invoking tool '{tool_name}': {e}") from e
        except httpx.HTTPStatusError as e:
            raise MCPClientError(f"Server error invoking tool '{tool_name}': {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            raise MCPClientError(f"Unexpected error invoking tool '{tool_name}': {e}") from e

    async def retrieve_documents(
        self, 
        tool_name: str, 
        query_text: str, 
        k: int = 5
    ) -> Dict[str, Any]:
        """Invokes a document retriever tool"""
        print(f"MCP Client: Invoking document retriever tool '{tool_name}' with query text: {query_text[:min(len(query_text), 50)]}...")
        if not tool_name:
            raise ValueError("tool_name cannot be empty.")
        if not query_text:
            raise ValueError("query_text cannot be empty.")
        if not 0 < k <= 100:
            raise ValueError("k must be a positive integer between 1 and 100.")
        params = {"query_text": query_text, "k": k}
        return await self.invoke_tool(tool_name, params)

    async def close(self):
        """Closes the httpx client."""
        await self._client.aclose() 