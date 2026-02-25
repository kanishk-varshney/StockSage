"""Web search tool using SerperDevTool for live news and market research."""

from crewai_tools import SerperDevTool


def create_search_tool() -> SerperDevTool:
    """Create a SerperDevTool instance for live web search.

    Requires SERPER_API_KEY environment variable to be set.
    Get a free key at https://serper.dev/
    """
    # Keep result volume compact to avoid large prompt payloads and TPM spikes.
    return SerperDevTool(n_results=3)
