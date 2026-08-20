# KeepStone MCP Server

Model Context Protocol (MCP) server for [KeepStone](https://github.com/dhanoopk/keepstone) - AI-powered artifact management.

This allows Claude and other MCP-compatible AI assistants to interact with your KeepStone instance.

## Features

- **Artifact Management**: List, get, create, update, and delete artifacts
- **Search**: Full-text search and AI-powered semantic search
- **Project Management**: List projects and get project-specific artifacts
- **Expiry Tracking**: Monitor expiring and expired artifacts

## Prerequisites

1. A running KeepStone instance with the REST API enabled
2. An API key from KeepStone (generate in Settings > API Keys)

## Installation

### Install with Claude CLI

```bash
claude add mcp keepstone
```

### Manual Installation

1. Install the package:

```bash
pip install keepstone-mcp
```

2. Configure Claude Code by adding to your Claude settings:

**~/.claude/settings.json** (user level) or **.claude/settings.json** (project level):

```json
{
  "mcpServers": {
    "keepstone": {
      "command": "uvx",
      "args": ["keepstone-mcp"],
      "env": {
        "KEEPSTONE_URL": "https://your-keepstone-instance.com",
        "KEEPSTONE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Configuration

Set the following environment variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `KEEPSTONE_URL` | Base URL of your KeepStone instance | Yes | `http://localhost:5000` |
| `KEEPSTONE_API_KEY` | API key from KeepStone settings | Yes | - |

## Available Tools

### Artifact Tools

| Tool | Description |
|------|-------------|
| `list_artifacts` | List all artifacts with optional filters |
| `get_artifact` | Get a specific artifact by ID |
| `create_artifact` | Create a new artifact |
| `update_artifact` | Update an existing artifact |
| `delete_artifact` | Delete an artifact |
| `search_artifacts` | Text search in artifacts |
| `semantic_search` | AI-powered semantic search |

### Project Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all projects |
| `get_project` | Get a specific project |
| `get_project_artifacts` | Get artifacts in a project |
| `get_project_types` | Get artifact types for a project |

### Expiry Tools

| Tool | Description |
|------|-------------|
| `list_expiring_artifacts` | List artifacts expiring soon |
| `list_expired_artifacts` | List all expired artifacts |

## Usage Examples

Once configured, you can ask Claude:

- "List all my artifacts in KeepStone"
- "Search for AWS tokens in KeepStone"
- "Create a new note in KeepStone with the title 'Meeting Notes'"
- "Show me all expired artifacts"
- "What projects do I have in KeepStone?"

## Generating an API Key

1. Log in to your KeepStone instance
2. Go to Settings > API Keys
3. Click "Create API Key"
4. Give it a name and select appropriate permissions
5. Copy the key immediately (it won't be shown again)

## Development

```bash
# Clone the repository
git clone https://github.com/dhanoopk/keepstone.git
cd keepstone/mcp_server

# Install in development mode
pip install -e ".[dev]"

# Run the server directly
python -m keepstone_mcp.server
```

# Adding to claude code

1. Run 
`uvx --from /home/dhanoop/projects/keepstone/mcp_server keepstone-mcp`                      
                                                                                              
2. Update the mcp server config part in to .claude.json:                                                                      
`                                                                                            
  "keepstone": {                                                                              
    "command": "uvx",                                                                         
    "args": ["--from", "/home/dhanoop/projects/keepstone/mcp_server", "keepstone-mcp"],       
    "env": {                                                                                  
      "KEEPSTONE_URL": "http://localhost:2222",                                               
      "KEEPSTONE_API_KEY": "your api key here" 
    }                                                                                         
  }  
`
## License

MIT License - see [LICENSE](LICENSE) for details.
