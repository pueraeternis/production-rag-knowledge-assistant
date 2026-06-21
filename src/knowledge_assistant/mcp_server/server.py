"""
Deferred MCP SDK server registration (Plan 12).

Plan 10 delivers typed handler functions in ``tools.py`` without MCP SDK runtime.
Plan 12 will:

* add the ``mcp`` SDK dependency;
* register Tier 1 handlers as MCP tools;
* wire stdio or network transport;
* implement the MCP client in the LangGraph agent.

Handler names and Pydantic schemas in ``schemas.py`` are the stable contract surface.
"""
