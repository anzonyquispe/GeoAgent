#!/usr/bin/env python3
"""
Example 2: QGIS Integration via Model Context Protocol (MCP)
=============================================================

This example demonstrates how AI agents can interact with
professional GIS software (QGIS) through MCP - a protocol
that allows LLMs to call external tools.

MCP Architecture:
  User -> LLM -> MCP Server -> QGIS Operations -> Results

Run time: ~10 seconds (simulated, no QGIS required)
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List

print("=" * 60)
print("EXAMPLE 2: QGIS + MCP Integration")
print("=" * 60)

# ============================================================
# STEP 1: Define MCP Tool Schema
# ============================================================
print("\n[Step 1] Defining MCP Tool Schema...")

MCP_TOOLS = [
    {
        "name": "load_vector_layer",
        "description": "Load a vector layer (shapefile, GeoJSON) into QGIS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to vector file"},
                "layer_name": {"type": "string", "description": "Name for the layer"}
            },
            "required": ["path", "layer_name"]
        }
    },
    {
        "name": "buffer_analysis",
        "description": "Create buffer zones around features",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layer_name": {"type": "string"},
                "distance": {"type": "number", "description": "Buffer distance in meters"},
                "output_name": {"type": "string"}
            },
            "required": ["layer_name", "distance"]
        }
    },
    {
        "name": "spatial_join",
        "description": "Join attributes from one layer to another based on spatial relationship",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_layer": {"type": "string"},
                "join_layer": {"type": "string"},
                "predicate": {"type": "string", "enum": ["intersects", "contains", "within"]}
            },
            "required": ["target_layer", "join_layer"]
        }
    },
    {
        "name": "calculate_area",
        "description": "Calculate area of polygons in hectares",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layer_name": {"type": "string"},
                "output_column": {"type": "string"}
            },
            "required": ["layer_name"]
        }
    }
]

print(f"  Registered {len(MCP_TOOLS)} QGIS tools for MCP")
for tool in MCP_TOOLS:
    print(f"    - {tool['name']}: {tool['description'][:50]}...")

# ============================================================
# STEP 2: Simulate MCP Server
# ============================================================
print("\n[Step 2] Simulating MCP Server...")

@dataclass
class QGISLayer:
    name: str
    feature_count: int
    geometry_type: str

class SimulatedQGISMCPServer:
    """
    Simulates a QGIS MCP Server that would normally connect
    to a running QGIS instance via PyQGIS.

    In production, this would execute real QGIS operations.
    """

    def __init__(self):
        self.layers: Dict[str, QGISLayer] = {}
        print("  MCP Server initialized")

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results."""
        print(f"\n  [MCP] Executing: {name}")
        print(f"         Arguments: {arguments}")

        if name == "load_vector_layer":
            layer = QGISLayer(
                name=arguments["layer_name"],
                feature_count=1815,  # Simulated
                geometry_type="MultiPolygon"
            )
            self.layers[layer.name] = layer
            return {"status": "success", "features_loaded": layer.feature_count}

        elif name == "buffer_analysis":
            output = arguments.get("output_name", f"{arguments['layer_name']}_buffer")
            self.layers[output] = QGISLayer(output, 1815, "MultiPolygon")
            return {"status": "success", "output_layer": output}

        elif name == "spatial_join":
            return {"status": "success", "features_joined": 1500}

        elif name == "calculate_area":
            return {"status": "success", "total_area_ha": 1285216.5}

        return {"status": "error", "message": "Unknown tool"}

# ============================================================
# STEP 3: Simulate LLM -> MCP Workflow
# ============================================================
print("\n[Step 3] Simulating LLM -> MCP Workflow...")

user_query = """
I have fire points and municipality boundaries.
Calculate how many fires are within 5km of protected areas.
"""

print(f"\nUser Query: {user_query.strip()}")

print("\n[LLM Planning]")
print("  1. Load protected areas layer")
print("  2. Create 5km buffer around protected areas")
print("  3. Spatial join fire points with buffers")
print("  4. Count fires within buffers")

# Execute via MCP
server = SimulatedQGISMCPServer()

# Step 1: Load layers
result1 = server.call_tool("load_vector_layer", {
    "path": "protected_areas.shp",
    "layer_name": "protected_areas"
})

result2 = server.call_tool("load_vector_layer", {
    "path": "fire_points.geojson",
    "layer_name": "fires"
})

# Step 2: Buffer analysis
result3 = server.call_tool("buffer_analysis", {
    "layer_name": "protected_areas",
    "distance": 5000,
    "output_name": "protected_5km_buffer"
})

# Step 3: Spatial join
result4 = server.call_tool("spatial_join", {
    "target_layer": "fires",
    "join_layer": "protected_5km_buffer",
    "predicate": "within"
})

print("\n[LLM Response]")
print("-" * 40)
print(f"""
Analysis complete using QGIS via MCP:

- Protected areas loaded: {result1['features_loaded']} features
- 5km buffer zones created
- Fires within buffer: {result4['features_joined']} fires

This means {result4['features_joined']} fire detections occurred
within 5km of protected areas, indicating potential threats
to conservation zones.
""")

# ============================================================
# STEP 4: MCP Configuration Example
# ============================================================
print("\n" + "=" * 60)
print("MCP CONFIGURATION")
print("=" * 60)

mcp_config = {
    "mcpServers": {
        "qgis-tools": {
            "command": "python",
            "args": ["qgis_mcp_server.py"],
            "cwd": "/path/to/geoagent",
            "env": {"PYTHONPATH": "."}
        }
    }
}

print("\n.mcp.json configuration:")
print(json.dumps(mcp_config, indent=2))

print("""
This configuration tells Claude Code how to start
the QGIS MCP server, enabling natural language
interaction with GIS operations.

Example conversation:
  User: "Load the municipalities shapefile and calculate areas"
  Claude: [Calls load_vector_layer, then calculate_area via MCP]
  Claude: "I've loaded 1,815 municipalities. Total area: 1.28M hectares"
""")

print("=" * 60)
print("Example completed successfully!")
print("=" * 60)
