from pathlib import Path

from mcp.server.fastmcp import FastMCP

from tools import (
    analyze_peru_fires,
    download_ctry_shp,
    download_viirs_snpp_peru,
    fires_clean,
    intersect_and_collapse_fires_peru,
    plot_fires_choropleth_peru,
)

SCRIPT_DIR = Path(__file__).parent.resolve()

mcp = FastMCP("peru-wildfire-analysis")

# Register the existing tool functions directly - their docstrings become the
# tool descriptions Claude Desktop uses to decide when/how to call them.
mcp.tool()(download_viirs_snpp_peru)
mcp.tool()(fires_clean)
mcp.tool()(download_ctry_shp)
mcp.tool()(intersect_and_collapse_fires_peru)
mcp.tool()(plot_fires_choropleth_peru)
mcp.tool()(analyze_peru_fires)


@mcp.prompt()
def peru_fire_analysis_workflow() -> str:
    """Step-by-step guidance for analyzing Peru wildfires with this server's tools."""
    return (SCRIPT_DIR / "SKILL.md").read_text()


if __name__ == "__main__":
    mcp.run()
