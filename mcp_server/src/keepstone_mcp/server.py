#!/usr/bin/env python3
"""
KeepStone MCP Server - Model Context Protocol server for KeepStone.

This server exposes KeepStone functionality as MCP tools via REST API calls.
Install with: claude add mcp keepstone-mcp
Configure with environment variables:
  - KEEPSTONE_URL: Base URL of your KeepStone instance (default: http://localhost:5000)
  - KEEPSTONE_API_KEY: Your API key from KeepStone settings
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Configuration
KEEPSTONE_URL = os.environ.get("KEEPSTONE_URL", "http://localhost:5000")
KEEPSTONE_API_KEY = os.environ.get("KEEPSTONE_API_KEY", "")


class KeepStoneClient:
    """HTTP client for KeepStone REST API"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the KeepStone API"""
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                **kwargs
            )

        if response.status_code >= 400:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            raise Exception(f"API error {response.status_code}: {error_data.get('error', response.text)}")

        return response.json()

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        return await self.request("POST", path, json=json_data)

    async def put(self, path: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        return await self.request("PUT", path, json=json_data)

    async def delete(self, path: str) -> Dict[str, Any]:
        return await self.request("DELETE", path)


# Initialize client
client = KeepStoneClient(KEEPSTONE_URL, KEEPSTONE_API_KEY)

# Initialize MCP server
server = Server("keepstone-mcp")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools"""
    return [
        # Artifact tools
        Tool(
            name="list_artifacts",
            description="List all artifacts in KeepStone. Optionally filter by project or type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "Filter by project ID"},
                    "type_name": {"type": "string", "description": "Filter by artifact type"},
                    "search": {"type": "string", "description": "Search in name and content"},
                    "limit": {"type": "integer", "description": "Max results (default: 50)"},
                },
            },
        ),
        Tool(
            name="get_artifact",
            description="Get detailed information about a specific artifact by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "integer", "description": "The artifact ID"},
                },
                "required": ["artifact_id"],
            },
        ),
        Tool(
            name="create_artifact",
            description="Create a new artifact (token, note, certificate, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the artifact"},
                    "content": {"type": "string", "description": "Content/text of the artifact"},
                    "type_name": {"type": "string", "description": "Type (Token, Note, Certificate, etc.)"},
                    "project_id": {"type": "integer", "description": "Project ID"},
                    "expiry_date": {"type": "string", "description": "Expiry date (YYYY-MM-DD)"},
                },
                "required": ["name", "content", "type_name"],
            },
        ),
        Tool(
            name="update_artifact",
            description="Update an existing artifact's properties.",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "integer", "description": "The artifact ID"},
                    "name": {"type": "string", "description": "New name"},
                    "content": {"type": "string", "description": "New content"},
                    "type_name": {"type": "string", "description": "New type"},
                    "expiry_date": {"type": "string", "description": "New expiry date (YYYY-MM-DD)"},
                },
                "required": ["artifact_id"],
            },
        ),
        Tool(
            name="delete_artifact",
            description="Delete an artifact by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "integer", "description": "The artifact ID"},
                },
                "required": ["artifact_id"],
            },
        ),
        Tool(
            name="search_artifacts",
            description="Search artifacts by text in name or content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "project_id": {"type": "integer", "description": "Filter by project ID"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="semantic_search",
            description="Perform AI-powered semantic search to find relevant artifacts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "k": {"type": "integer", "description": "Number of results (default: 5)"},
                },
                "required": ["query"],
            },
        ),
        # Project tools
        Tool(
            name="list_projects",
            description="List all projects in KeepStone.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_project",
            description="Get detailed information about a specific project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The project ID"},
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_project_artifacts",
            description="Get all artifacts in a specific project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The project ID"},
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_project_types",
            description="Get configured artifact types for a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "description": "The project ID"},
                },
                "required": ["project_id"],
            },
        ),
        # Expiry tracking tools
        Tool(
            name="list_expiring_artifacts",
            description="List artifacts expiring soon or already expired.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Days to look ahead (default: 14)"},
                    "include_expired": {"type": "boolean", "description": "Include already expired (default: true)"},
                },
            },
        ),
        Tool(
            name="list_expired_artifacts",
            description="List all artifacts that have already expired.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "list_artifacts":
            params = {}
            if "project_id" in arguments:
                params["project_id"] = arguments["project_id"]
            if "type_name" in arguments:
                params["type_name"] = arguments["type_name"]
            if "search" in arguments:
                params["search"] = arguments["search"]
            if "limit" in arguments:
                params["limit"] = arguments["limit"]

            result = await client.get("/api/v1/artifacts", params=params)
            return [TextContent(type="text", text=json.dumps(result["data"], indent=2))]

        elif name == "get_artifact":
            artifact_id = arguments["artifact_id"]
            result = await client.get(f"/api/v1/artifacts/{artifact_id}")
            return [TextContent(type="text", text=json.dumps(result["data"]["artifact"], indent=2))]

        elif name == "create_artifact":
            data = {
                "name": arguments["name"],
                "content": arguments["content"],
                "type_name": arguments["type_name"],
            }
            if "project_id" in arguments:
                data["project_id"] = arguments["project_id"]
            if "expiry_date" in arguments:
                data["expiry_date"] = arguments["expiry_date"]

            result = await client.post("/api/v1/artifacts", json_data=data)
            return [TextContent(type="text", text=json.dumps({"success": True, "artifact": result["data"]["artifact"]}, indent=2))]

        elif name == "update_artifact":
            artifact_id = arguments["artifact_id"]
            data = {}
            for key in ["name", "content", "type_name", "expiry_date"]:
                if key in arguments:
                    data[key] = arguments[key]

            result = await client.put(f"/api/v1/artifacts/{artifact_id}", json_data=data)
            return [TextContent(type="text", text=json.dumps({"success": True, "artifact": result["data"]["artifact"]}, indent=2))]

        elif name == "delete_artifact":
            artifact_id = arguments["artifact_id"]
            result = await client.delete(f"/api/v1/artifacts/{artifact_id}")
            return [TextContent(type="text", text=json.dumps({"success": True, "message": result.get("message", "Deleted")}))]

        elif name == "search_artifacts":
            params = {"q": arguments["query"]}
            if "project_id" in arguments:
                params["project_id"] = arguments["project_id"]

            result = await client.get("/api/v1/artifacts/search", params=params)
            return [TextContent(type="text", text=json.dumps(result["data"]["artifacts"], indent=2))]

        elif name == "semantic_search":
            data = {"query": arguments["query"]}
            if "k" in arguments:
                data["k"] = arguments["k"]

            result = await client.post("/api/v1/artifacts/semantic-search", json_data=data)
            return [TextContent(type="text", text=json.dumps(result["data"]["results"], indent=2))]

        elif name == "list_projects":
            result = await client.get("/api/v1/projects")
            return [TextContent(type="text", text=json.dumps(result["data"]["projects"], indent=2))]

        elif name == "get_project":
            project_id = arguments["project_id"]
            result = await client.get(f"/api/v1/projects/{project_id}")
            return [TextContent(type="text", text=json.dumps(result["data"]["project"], indent=2))]

        elif name == "get_project_artifacts":
            project_id = arguments["project_id"]
            result = await client.get(f"/api/v1/projects/{project_id}/artifacts")
            return [TextContent(type="text", text=json.dumps(result["data"]["artifacts"], indent=2))]

        elif name == "get_project_types":
            project_id = arguments["project_id"]
            result = await client.get(f"/api/v1/projects/{project_id}/types")
            return [TextContent(type="text", text=json.dumps(result["data"], indent=2))]

        elif name == "list_expiring_artifacts":
            params = {}
            if "days" in arguments:
                params["days"] = arguments["days"]
            if "include_expired" in arguments:
                params["include_expired"] = str(arguments["include_expired"]).lower()

            result = await client.get("/api/v1/artifacts/expiring", params=params)
            return [TextContent(type="text", text=json.dumps(result["data"]["artifacts"], indent=2))]

        elif name == "list_expired_artifacts":
            result = await client.get("/api/v1/artifacts/expired")
            return [TextContent(type="text", text=json.dumps(result["data"]["artifacts"], indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """Entry point for the CLI"""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run()
