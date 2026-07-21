"""Standalone MCP server exposing the knowledge base as tools.

Run in its OWN environment (see backend/requirements-mcp.txt) — fastmcp requires a newer
starlette than the FastAPI backend, so it must not share the main venv.

    pip install -r requirements-mcp.txt
    python -m app.mcp_server.server

Connectable from Claude Desktop / Cursor via Streamable HTTP on port 8421.
"""

from fastmcp import FastMCP

from app.mcp_server.tools import (
    ask_knowledge_worker_impl,
    list_documents_impl,
    search_documents_impl,
)

mcp = FastMCP("AgenticKnowledgeWorker")


@mcp.tool()
async def search_documents(query: str, top_k: int = 5) -> str:
    """Search the knowledge base for relevant document chunks.

    Args:
        query: Natural language search query.
        top_k: Number of results to return (default 5).
    """
    return await search_documents_impl(query, top_k)


@mcp.tool()
async def ask_knowledge_worker(question: str) -> str:
    """Ask the Agentic Knowledge Worker a question about the uploaded documents.

    Runs the full multi-agent pipeline and returns a grounded, cited answer.

    Args:
        question: The question to ask.
    """
    return await ask_knowledge_worker_impl(question)


@mcp.tool()
async def list_documents() -> str:
    """List all uploaded documents in the knowledge base."""
    return await list_documents_impl()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8421)
