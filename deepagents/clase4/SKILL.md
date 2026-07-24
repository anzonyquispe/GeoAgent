---
name: peru-fire-analysis
description: Analyze and visualize NASA VIIRS wildfire data for Peru using MCP tools
---

# Peru Fire Analysis (MCP)

## Overview
This MCP server exposes tools to download, process, and visualize NASA VIIRS-SNPP
satellite fire detection data for Peru. Tools share state within one server
session - call them in sequence. The final map is returned as an inline PNG image.

## When to Use
- User asks to analyze wildfires or active fires in Peru
- User needs fire counts by department
- User wants to visualize fire data on a map
- User mentions VIIRS, FIRMS, or NASA fire data

## Fast path
Call `analyze_peru_fires(year)` to run the whole download -> clean -> boundaries ->
aggregate pipeline in one tool call, then call `plot_fires_choropleth_peru()` to
get the map image.

## Step-by-step workflow (equivalent, more control)

1. `download_viirs_snpp_peru(year=2024)` - Download fire data
2. `fires_clean()` - Convert to GeoDataFrame with geometry
3. `download_ctry_shp()` - Download Peru department boundaries
4. `intersect_and_collapse_fires_peru(level="year")` - Spatially join and aggregate
5. `plot_fires_choropleth_peru()` - Render and return the choropleth as a PNG image

## Important Notes

- VIIRS-SNPP data available from 2012 to current year
- Tools must be called in this order - later steps depend on state set by earlier ones
- The map is a static PNG rendered inline in the chat (no file downloads needed)
