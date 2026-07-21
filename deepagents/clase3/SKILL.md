---
name: peru-fire-analysis
description: Analyze and visualize NASA VIIRS wildfire data for Peru using geospatial tools
---

# Peru Fire Analysis

## Overview
This skill provides tools to download, process, and visualize NASA VIIRS-SNPP satellite fire detection data for Peru. Tools share state automatically - call them in sequence. Maps are displayed directly in the chat.

## When to Use
- User asks to analyze wildfires or active fires in Peru
- User needs fire counts by region, department, or province
- User wants to visualize fire data on a map
- User mentions VIIRS, FIRMS, or NASA fire data

## Tools Reference

### 1. download_viirs_snpp_peru
**Purpose:** Download NASA FIRMS VIIRS-SNPP fire detection data for Peru.

**Parameters:**
- `year` (int, required): Year to fetch (2012 to current year)

**Returns:** Confirmation message with fire count.

---

### 2. fires_clean
**Purpose:** Convert downloaded fire data into a GeoDataFrame with geometry. Call after download_viirs_snpp_peru.

**Parameters:** None

**Returns:** Confirmation message with statistics.

---

### 3. download_ctry_shp
**Purpose:** Download Peru administrative boundary polygons (departments) from GADM.

**Parameters:** None

**Returns:** Confirmation message with region list.

---

### 4. intersect_and_collapse_fires_peru
**Purpose:** Spatially join fires with boundaries and aggregate counts. Call after fires_clean and download_ctry_shp.

**Parameters:**
- `level` (str, optional): "year" (default) or "year_month"

**Returns:** Summary with top 5 regions by fire count.

---

### 5. folium_choropleth_peru
**Purpose:** Create interactive choropleth map displayed in the chat. Call after intersect_and_collapse_fires_peru.

**Parameters:** None (no file output - map renders inline)

**Returns:** Confirmation that the map will be displayed.

---

## Workflow

Execute tools in this order:

1. `download_viirs_snpp_peru(year=2024)` - Download fire data
2. `fires_clean()` - Convert to GeoDataFrame
3. `download_ctry_shp()` - Download Peru boundaries
4. `intersect_and_collapse_fires_peru()` - Aggregate by region
5. `folium_choropleth_peru()` - Create and display map in chat

## Important Notes

- VIIRS-SNPP data available from 2012 to current year
- Tools must be called in sequence (they share state)
- Maps render directly in the Streamlit chat - no file downloads needed
- Interactive tooltips show region names and fire counts on hover
