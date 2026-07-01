#!/usr/bin/env python3
"""
Example 4: Model Context Protocol (MCP) Demonstration
======================================================

This example demonstrates how MCP enables AI assistants to
control external tools like QGIS through a standardized protocol.

What is MCP?
------------
MCP (Model Context Protocol) is an open standard by Anthropic that
allows AI assistants to securely connect to external tools and data.

Think of it as a "USB port for AI" - a universal way to plug in
any tool or data source.

Key Components:
- MCP Host: The AI application (Claude Desktop, IDE)
- MCP Server: Exposes tools/data to the AI
- MCP Client: Connects host to servers
- Transport: Communication layer (stdio, HTTP, SSE)

Run time: ~5 seconds (simulated, no QGIS required)
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable
from datetime import datetime

print("=" * 70)
print("EXAMPLE 4: Model Context Protocol (MCP) Demonstration")
print("=" * 70)

# ============================================================
# PART 1: What is MCP?
# ============================================================
print("\n" + "=" * 70)
print("PART 1: Understanding MCP")
print("=" * 70)

print("""
Model Context Protocol (MCP) is an OPEN STANDARD that enables:

  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
  │  Claude/LLM     │ ←→  │   MCP Protocol  │ ←→  │  External Tools │
  │  (AI Assistant) │     │   (JSON-RPC)    │     │  (QGIS, DBs...) │
  └─────────────────┘     └─────────────────┘     └─────────────────┘

Why MCP matters:
----------------
1. UNIVERSAL: One protocol works with any AI + any tool
2. SECURE: Controlled access to external resources
3. DISCOVERABLE: AI can learn what tools are available
4. COMPOSABLE: Chain multiple tools together

Without MCP: Custom integration for each AI-tool pair (N × M problem)
With MCP:    Standard interface for all combinations (N + M solution)
""")

# ============================================================
# PART 2: Available MCP Servers
# ============================================================
print("\n" + "=" * 70)
print("PART 2: Available MCP Servers (Ecosystem)")
print("=" * 70)

MCP_SERVERS = {
    "Geospatial": [
        ("qgis-mcp", "Control QGIS for spatial analysis"),
        ("postgis-mcp", "PostGIS spatial database queries"),
        ("overpass-mcp", "OpenStreetMap Overpass API"),
        ("mapbox-mcp", "Mapbox geocoding and maps"),
    ],
    "Databases": [
        ("postgres-mcp", "PostgreSQL database operations"),
        ("sqlite-mcp", "SQLite local databases"),
        ("bigquery-mcp", "Google BigQuery analytics"),
        ("mysql-mcp", "MySQL database access"),
    ],
    "Development": [
        ("github-mcp", "GitHub API (repos, issues, PRs)"),
        ("git-mcp", "Local git operations"),
        ("docker-mcp", "Docker container management"),
        ("filesystem-mcp", "File system operations"),
    ],
    "Web & APIs": [
        ("fetch-mcp", "HTTP requests to any API"),
        ("brave-search-mcp", "Web search via Brave"),
        ("slack-mcp", "Slack messaging"),
        ("gmail-mcp", "Gmail operations"),
    ],
    "Data Science": [
        ("jupyter-mcp", "Jupyter notebook execution"),
        ("pandas-mcp", "DataFrame operations"),
        ("duckdb-mcp", "DuckDB analytical queries"),
    ],
}

print("\nAvailable MCP Servers by Category:\n")
for category, servers in MCP_SERVERS.items():
    print(f"  {category}:")
    for name, description in servers:
        print(f"    • {name:<20} - {description}")
    print()

print("  Registry: https://github.com/modelcontextprotocol/servers")

# ============================================================
# PART 3: Simulated MCP Server Implementation
# ============================================================
print("\n" + "=" * 70)
print("PART 3: Building an MCP Server (Simplified)")
print("=" * 70)

@dataclass
class MCPTool:
    """Represents a tool exposed by an MCP server."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable

@dataclass
class MCPServer:
    """
    Simulated MCP Server for QGIS operations.

    In production, this would:
    1. Connect to a running QGIS instance via PyQGIS
    2. Expose tools via JSON-RPC over stdio/HTTP
    3. Handle authentication and permissions
    """
    name: str
    version: str = "1.0.0"
    tools: Dict[str, MCPTool] = field(default_factory=dict)
    _layers: Dict[str, dict] = field(default_factory=dict)

    def register_tool(self, name: str, description: str,
                      parameters: Dict, handler: Callable):
        """Register a tool that can be called by the AI."""
        self.tools[name] = MCPTool(name, description, parameters, handler)
        print(f"  [MCP] Registered tool: {name}")

    def list_tools(self) -> List[Dict]:
        """Return tool definitions in MCP format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": list(tool.parameters.keys())
                }
            }
            for tool in self.tools.values()
        ]

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Execute a tool and return results."""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}

        tool = self.tools[name]
        print(f"\n  [MCP] Executing: {name}")
        print(f"        Arguments: {json.dumps(arguments, indent=2)}")

        result = tool.handler(self, **arguments)
        print(f"        Result: {json.dumps(result, indent=2)}")
        return result

# Create QGIS MCP Server
print("\nInitializing QGIS MCP Server...\n")
qgis_server = MCPServer(name="qgis-mcp")

# Register tools
def load_vector_layer(server, path: str, layer_name: str = None):
    """Load a vector layer into QGIS."""
    name = layer_name or path.split("/")[-1].replace(".shp", "")
    server._layers[name] = {
        "path": path,
        "type": "vector",
        "features": 1815,  # Simulated
        "geometry": "MultiPolygon"
    }
    return {"status": "success", "layer": name, "features": 1815}

def buffer_analysis(server, layer_name: str, distance: float, output_name: str = None):
    """Create buffer zones around features."""
    output = output_name or f"{layer_name}_buffer_{int(distance)}m"
    server._layers[output] = {
        "type": "vector",
        "geometry": "MultiPolygon",
        "source": f"buffer({layer_name}, {distance}m)"
    }
    return {"status": "success", "output_layer": output, "buffer_distance": distance}

def spatial_join(server, target_layer: str, join_layer: str, predicate: str = "intersects"):
    """Join attributes based on spatial relationship."""
    return {
        "status": "success",
        "features_matched": 1500,  # Simulated
        "predicate": predicate
    }

def calculate_area(server, layer_name: str, unit: str = "hectares"):
    """Calculate area of polygon features."""
    return {
        "status": "success",
        "total_area": 1285216.5,
        "unit": unit,
        "features_processed": server._layers.get(layer_name, {}).get("features", 0)
    }

def get_layer_info(server, layer_name: str):
    """Get information about a layer."""
    if layer_name in server._layers:
        return {"status": "success", "layer": server._layers[layer_name]}
    return {"status": "error", "message": f"Layer '{layer_name}' not found"}

# Register all tools
qgis_server.register_tool(
    "load_vector_layer",
    "Load a vector layer (shapefile, GeoJSON) into QGIS",
    {"path": {"type": "string"}, "layer_name": {"type": "string"}},
    load_vector_layer
)

qgis_server.register_tool(
    "buffer_analysis",
    "Create buffer zones around features at specified distance",
    {"layer_name": {"type": "string"}, "distance": {"type": "number"}, "output_name": {"type": "string"}},
    buffer_analysis
)

qgis_server.register_tool(
    "spatial_join",
    "Join attributes from one layer to another based on spatial relationship",
    {"target_layer": {"type": "string"}, "join_layer": {"type": "string"}, "predicate": {"type": "string"}},
    spatial_join
)

qgis_server.register_tool(
    "calculate_area",
    "Calculate area of polygon features in specified units",
    {"layer_name": {"type": "string"}, "unit": {"type": "string"}},
    calculate_area
)

qgis_server.register_tool(
    "get_layer_info",
    "Get information about a loaded layer",
    {"layer_name": {"type": "string"}},
    get_layer_info
)

# ============================================================
# PART 4: Simulated AI Interaction
# ============================================================
print("\n" + "=" * 70)
print("PART 4: AI Assistant Using MCP Tools")
print("=" * 70)

user_query = """
I have fire point data and protected areas polygons.
Find all fires within 5km of protected areas and tell me how many there are.
"""

print(f"\n[USER QUERY]\n{user_query.strip()}")

print("\n[AI REASONING]")
print("  1. User wants to analyze fires near protected areas")
print("  2. Need to load both layers first")
print("  3. Create 5km buffer around protected areas")
print("  4. Spatial join to find fires within buffer")
print("  5. Report the count")

print("\n[AI TOOL CALLS VIA MCP]")
print("-" * 50)

# Step 1: Load protected areas
result1 = qgis_server.call_tool("load_vector_layer", {
    "path": "/data/protected_areas.shp",
    "layer_name": "protected_areas"
})

# Step 2: Load fire points
result2 = qgis_server.call_tool("load_vector_layer", {
    "path": "/data/fire_detections_2024.geojson",
    "layer_name": "fires"
})

# Step 3: Create buffer
result3 = qgis_server.call_tool("buffer_analysis", {
    "layer_name": "protected_areas",
    "distance": 5000,
    "output_name": "protected_5km_buffer"
})

# Step 4: Spatial join
result4 = qgis_server.call_tool("spatial_join", {
    "target_layer": "fires",
    "join_layer": "protected_5km_buffer",
    "predicate": "within"
})

print("\n" + "-" * 50)
print("[AI RESPONSE TO USER]")
print("-" * 50)
print(f"""
Based on my analysis using QGIS:

📊 Analysis Results:
   • Protected areas loaded: {result1['features']} features
   • Fire detections loaded: {result2['features']} points
   • Buffer zone created: 5km around protected areas
   • Fires within buffer: {result4['features_matched']} fire detections

🔥 Finding: {result4['features_matched']} fires ({result4['features_matched']/result2['features']*100:.1f}%)
   were detected within 5km of protected areas in 2024.

⚠️  Policy Implication:
   This represents a significant threat to conservation zones.
   Recommend increased monitoring and rapid response capabilities
   in these buffer areas.
""")

# ============================================================
# PART 5: MCP Configuration
# ============================================================
print("\n" + "=" * 70)
print("PART 5: How to Configure MCP in Claude Desktop")
print("=" * 70)

mcp_config = {
    "mcpServers": {
        "qgis-tools": {
            "command": "python",
            "args": ["-m", "qgis_mcp_server"],
            "cwd": "/path/to/geoagent",
            "env": {
                "QGIS_PREFIX_PATH": "/usr/share/qgis",
                "PYTHONPATH": "/usr/share/qgis/python"
            }
        },
        "postgres": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "env": {
                "DATABASE_URL": "postgresql://user:pass@localhost/geodata"
            }
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
        }
    }
}

print("\nExample ~/.config/claude/claude_desktop_config.json:\n")
print(json.dumps(mcp_config, indent=2))

print("""

How to set up:
--------------
1. Install Claude Desktop
2. Create/edit the config file above
3. Restart Claude Desktop
4. Claude can now use QGIS, PostgreSQL, and file system!

Example prompts you can then use:
---------------------------------
• "Load the municipalities shapefile and calculate areas"
• "Query the database for fire statistics by region"
• "Read the CSV file and analyze the data"
""")

# ============================================================
# PART 6: Build Your Own MCP Server
# ============================================================
print("\n" + "=" * 70)
print("PART 6: Creating Your Own MCP Server")
print("=" * 70)

server_code = '''
# Example: Minimal MCP Server in Python
# Install: pip install mcp

from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-geo-tools")

@server.tool()
async def analyze_fires(year: int, country: str = "PER") -> str:
    """Analyze fire detections for a country and year."""
    # Your analysis code here
    fires = download_firms_data(year, country)
    result = aggregate_by_region(fires)
    return f"Found {len(fires)} fires in {country} for {year}"

@server.tool()
async def create_buffer(layer: str, distance: float) -> str:
    """Create buffer around geographic features."""
    output = run_buffer_analysis(layer, distance)
    return f"Buffer created: {output}"

# Run the server
if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
'''

print(server_code)

print("""
Key MCP Server Concepts:
------------------------
1. Use @server.tool() decorator to expose functions
2. Type hints become the tool's parameter schema
3. Docstring becomes the tool's description
4. Return value is sent back to the AI

The AI will:
1. Discover available tools on startup
2. Read descriptions to understand capabilities
3. Call tools when user requests require them
4. Use results to formulate responses
""")

print("=" * 70)
print("Example completed successfully!")
print("=" * 70)
print("\nNext steps:")
print("  • Install MCP: pip install mcp")
print("  • Browse servers: https://github.com/modelcontextprotocol/servers")
print("  • Read docs: https://modelcontextprotocol.io")
print("=" * 70)
