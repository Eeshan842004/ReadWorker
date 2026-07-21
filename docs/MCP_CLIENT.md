# Connecting the MCP server to Claude Desktop / Cursor

The MCP server (`backend/app/mcp_server/server.py`) exposes three tools over Streamable
HTTP on port **8421**:

- `search_documents(query, top_k)` — raw hybrid-retrieval hits
- `ask_knowledge_worker(question)` — full multi-agent, cited answer
- `list_documents()` — everything in the knowledge base

## Run it (separate env from the API — see requirements-mcp.txt)

```bash
cd backend
python -m venv venv-mcp && source venv-mcp/Scripts/activate   # bin/activate on macOS/Linux
pip install -r requirements-mcp.txt
python -m app.mcp_server.server        # serves on http://localhost:8421
```

Or via Docker: `docker compose up mcp-server`.

## Claude Desktop config

Add to `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "agentic-knowledge-worker": {
      "url": "http://localhost:8421/mcp"
    }
  }
}
```

For stdio-based clients that spawn the process directly:

```json
{
  "mcpServers": {
    "agentic-knowledge-worker": {
      "command": "python",
      "args": ["-m", "app.mcp_server.server"],
      "cwd": "/absolute/path/to/backend",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb",
        "GROQ_API_KEY": "gsk_...",
        "GOOGLE_API_KEY": "AIza..."
      }
    }
  }
}
```

Restart the client; the three tools appear in its tool list.
