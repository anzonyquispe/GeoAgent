---
name: export-map
description: Export geospatial data to various map formats (Folium HTML, static image, KML)
---

# Map Export Skill

When the user invokes `/export-map`, create and export maps in various formats.

## Parameters
- **layer**: Name or path of the layer to map (required)
- **format**: Output format - html, png, kml (default: html)
- **style**: Map style - choropleth, points, heatmap (default: auto-detect)
- **output**: Output file path (optional)

## Supported Formats

### 1. Interactive HTML (Folium)
- Creates zoomable, interactive web maps
- Supports multiple tile providers (OSM, CartoDB, Stamen)
- Includes popups and tooltips

### 2. Static PNG/SVG (Matplotlib)
- Publication-quality static maps
- Customizable styling
- Supports north arrows and scale bars

### 3. KML/KMZ (Google Earth)
- Compatible with Google Earth
- Includes styling and descriptions

## Map Components

For choropleth maps:
- Color column selection
- Classification method (quantiles, equal interval, natural breaks)
- Legend generation

For point maps:
- Marker clustering for large datasets
- Custom marker icons
- Popup content configuration

## Example Usage
```
/export-map fires_2023 html
/export-map admin_regions png style=choropleth
/export-map points.geojson kml output=export.kml
```
