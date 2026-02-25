"""
QGIS MCP Server - Model Context Protocol server for geospatial operations.

This server exposes QGIS-like geospatial tools to Claude through the MCP protocol.

Usage:
    python qgis_mcp_server.py

Configure in .mcp.json:
    {
        "mcpServers": {
            "qgis": {
                "command": "python",
                "args": ["qgis_mcp_server.py"]
            }
        }
    }
"""

import asyncio
import json
from typing import Any, Optional
from pathlib import Path

# Geospatial imports
import geopandas as gpd
from shapely.geometry import shape
import pandas as pd

# MCP imports - install with: pip install mcp
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        Resource,
        ResourceContents,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP SDK not installed. Install with: pip install mcp")


class QGISMCPServer:
    """
    MCP Server that provides QGIS-like geospatial operations.

    This server exposes tools for:
    - Loading vector/raster layers
    - Performing spatial analysis
    - Exporting data to various formats

    Attributes
    ----------
    server : Server
        The MCP server instance
    layers : dict
        Dictionary storing loaded GeoDataFrames by name
    """

    def __init__(self):
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not available. Install with: pip install mcp")

        self.server = Server("qgis-mcp")
        self.layers: dict[str, gpd.GeoDataFrame] = {}
        self._setup_handlers()

    def _setup_handlers(self):
        """Register all MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return available QGIS tools."""
            return [
                Tool(
                    name="load_vector_layer",
                    description="Load a vector layer (GeoJSON, Shapefile, GeoPackage) into memory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the vector file"},
                            "layer_name": {"type": "string", "description": "Name to assign to the layer"},
                        },
                        "required": ["path", "layer_name"]
                    }
                ),
                Tool(
                    name="buffer_analysis",
                    description="Create buffer zones around features",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "layer_name": {"type": "string", "description": "Name of the layer"},
                            "distance": {"type": "number", "description": "Buffer distance in layer units"},
                            "output_name": {"type": "string", "description": "Name for the output layer"},
                        },
                        "required": ["layer_name", "distance", "output_name"]
                    }
                ),
                Tool(
                    name="spatial_join",
                    description="Perform spatial join between two layers",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "left_layer": {"type": "string", "description": "Name of the left layer"},
                            "right_layer": {"type": "string", "description": "Name of the right layer"},
                            "predicate": {"type": "string", "description": "Spatial predicate (intersects, within, contains)"},
                            "output_name": {"type": "string", "description": "Name for the output layer"},
                        },
                        "required": ["left_layer", "right_layer", "predicate", "output_name"]
                    }
                ),
                Tool(
                    name="get_layer_info",
                    description="Get information about a loaded layer (CRS, extent, feature count, columns)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "layer_name": {"type": "string", "description": "Name of the layer"}
                        },
                        "required": ["layer_name"]
                    }
                ),
                Tool(
                    name="export_layer",
                    description="Export a layer to file (GeoJSON, Shapefile, GeoPackage)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "layer_name": {"type": "string", "description": "Name of the layer to export"},
                            "output_path": {"type": "string", "description": "Output file path"},
                            "driver": {"type": "string", "description": "Output format: GeoJSON, ESRI Shapefile, GPKG"}
                        },
                        "required": ["layer_name", "output_path"]
                    }
                ),
                Tool(
                    name="clip_layer",
                    description="Clip one layer by another (like QGIS clip tool)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_layer": {"type": "string", "description": "Layer to be clipped"},
                            "clip_layer": {"type": "string", "description": "Layer to clip by"},
                            "output_name": {"type": "string", "description": "Name for the output layer"}
                        },
                        "required": ["input_layer", "clip_layer", "output_name"]
                    }
                ),
                Tool(
                    name="calculate_area",
                    description="Calculate area of polygon features",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "layer_name": {"type": "string", "description": "Name of the polygon layer"},
                            "area_column": {"type": "string", "description": "Name for the new area column"},
                            "unit": {"type": "string", "description": "Area unit: sqm, sqkm, hectares"}
                        },
                        "required": ["layer_name"]
                    }
                ),
                Tool(
                    name="dissolve",
                    description="Dissolve features based on an attribute",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "layer_name": {"type": "string", "description": "Name of the layer"},
                            "by_column": {"type": "string", "description": "Column to dissolve by"},
                            "output_name": {"type": "string", "description": "Name for the output layer"},
                            "aggfunc": {"type": "string", "description": "Aggregation function for other columns (sum, mean, first)"}
                        },
                        "required": ["layer_name", "output_name"]
                    }
                ),
                Tool(
                    name="reproject",
                    description="Reproject a layer to a different CRS",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "layer_name": {"type": "string", "description": "Name of the layer"},
                            "target_crs": {"type": "string", "description": "Target CRS (e.g., EPSG:4326, EPSG:32718)"},
                            "output_name": {"type": "string", "description": "Name for the output layer"}
                        },
                        "required": ["layer_name", "target_crs", "output_name"]
                    }
                ),
                Tool(
                    name="list_layers",
                    description="List all loaded layers",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Execute a QGIS tool."""
            try:
                if name == "load_vector_layer":
                    result = self._load_vector_layer(**arguments)
                elif name == "buffer_analysis":
                    result = self._buffer_analysis(**arguments)
                elif name == "spatial_join":
                    result = self._spatial_join(**arguments)
                elif name == "get_layer_info":
                    result = self._get_layer_info(**arguments)
                elif name == "export_layer":
                    result = self._export_layer(**arguments)
                elif name == "clip_layer":
                    result = self._clip_layer(**arguments)
                elif name == "calculate_area":
                    result = self._calculate_area(**arguments)
                elif name == "dissolve":
                    result = self._dissolve(**arguments)
                elif name == "reproject":
                    result = self._reproject(**arguments)
                elif name == "list_layers":
                    result = self._list_layers()
                else:
                    result = f"Unknown tool: {name}"

                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _load_vector_layer(self, path: str, layer_name: str) -> str:
        """Load a vector layer into memory."""
        gdf = gpd.read_file(path)
        self.layers[layer_name] = gdf
        return f"Loaded layer '{layer_name}' with {len(gdf)} features. CRS: {gdf.crs}"

    def _buffer_analysis(self, layer_name: str, distance: float, output_name: str) -> str:
        """Create buffer zones around features."""
        if layer_name not in self.layers:
            return f"Layer '{layer_name}' not found"

        gdf = self.layers[layer_name].copy()
        gdf['geometry'] = gdf.geometry.buffer(distance)
        self.layers[output_name] = gdf
        return f"Created buffer layer '{output_name}' with distance {distance}"

    def _spatial_join(self, left_layer: str, right_layer: str,
                      predicate: str, output_name: str) -> str:
        """Perform spatial join between two layers."""
        if left_layer not in self.layers or right_layer not in self.layers:
            return "One or both layers not found"

        left = self.layers[left_layer]
        right = self.layers[right_layer]

        result = gpd.sjoin(left, right, how="inner", predicate=predicate)
        self.layers[output_name] = result
        return f"Spatial join complete. Output '{output_name}' has {len(result)} features"

    def _get_layer_info(self, layer_name: str) -> str:
        """Get information about a layer."""
        if layer_name not in self.layers:
            return f"Layer '{layer_name}' not found"

        gdf = self.layers[layer_name]
        info = {
            "layer_name": layer_name,
            "crs": str(gdf.crs),
            "feature_count": len(gdf),
            "geometry_type": gdf.geometry.geom_type.unique().tolist(),
            "bounds": gdf.total_bounds.tolist(),
            "columns": gdf.columns.tolist(),
        }
        return json.dumps(info, indent=2)

    def _export_layer(self, layer_name: str, output_path: str,
                      driver: str = "GeoJSON") -> str:
        """Export a layer to file."""
        if layer_name not in self.layers:
            return f"Layer '{layer_name}' not found"

        gdf = self.layers[layer_name]
        gdf.to_file(output_path, driver=driver)
        return f"Exported '{layer_name}' to {output_path}"

    def _clip_layer(self, input_layer: str, clip_layer: str, output_name: str) -> str:
        """Clip one layer by another."""
        if input_layer not in self.layers or clip_layer not in self.layers:
            return "One or both layers not found"

        input_gdf = self.layers[input_layer]
        clip_gdf = self.layers[clip_layer]

        result = gpd.clip(input_gdf, clip_gdf)
        self.layers[output_name] = result
        return f"Clipped layer created as '{output_name}' with {len(result)} features"

    def _calculate_area(self, layer_name: str, area_column: str = "area",
                        unit: str = "sqm") -> str:
        """Calculate area of polygon features."""
        if layer_name not in self.layers:
            return f"Layer '{layer_name}' not found"

        gdf = self.layers[layer_name]

        # Calculate area in square meters first
        if gdf.crs and gdf.crs.is_geographic:
            # Project to equal area CRS for accurate area calculation
            gdf_proj = gdf.to_crs("ESRI:54009")  # World Mollweide
            area_sqm = gdf_proj.geometry.area
        else:
            area_sqm = gdf.geometry.area

        # Convert to requested unit
        if unit == "sqkm":
            gdf[area_column] = area_sqm / 1_000_000
        elif unit == "hectares":
            gdf[area_column] = area_sqm / 10_000
        else:
            gdf[area_column] = area_sqm

        self.layers[layer_name] = gdf
        return f"Added area column '{area_column}' in {unit} to layer '{layer_name}'"

    def _dissolve(self, layer_name: str, output_name: str,
                  by_column: str = None, aggfunc: str = "first") -> str:
        """Dissolve features based on an attribute."""
        if layer_name not in self.layers:
            return f"Layer '{layer_name}' not found"

        gdf = self.layers[layer_name]

        if by_column:
            result = gdf.dissolve(by=by_column, aggfunc=aggfunc)
        else:
            result = gdf.dissolve(aggfunc=aggfunc)

        self.layers[output_name] = result.reset_index()
        return f"Dissolved layer created as '{output_name}' with {len(result)} features"

    def _reproject(self, layer_name: str, target_crs: str, output_name: str) -> str:
        """Reproject a layer to a different CRS."""
        if layer_name not in self.layers:
            return f"Layer '{layer_name}' not found"

        gdf = self.layers[layer_name]
        result = gdf.to_crs(target_crs)
        self.layers[output_name] = result
        return f"Reprojected layer '{layer_name}' to {target_crs} as '{output_name}'"

    def _list_layers(self) -> str:
        """List all loaded layers."""
        if not self.layers:
            return "No layers loaded"

        info = []
        for name, gdf in self.layers.items():
            info.append({
                "name": name,
                "features": len(gdf),
                "crs": str(gdf.crs),
                "geometry_type": gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else "empty"
            })
        return json.dumps(info, indent=2)

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Entry point for the MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP SDK not installed.")
        print("Install with: pip install mcp")
        return

    server = QGISMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
