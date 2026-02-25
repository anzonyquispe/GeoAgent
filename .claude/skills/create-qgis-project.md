---
name: create-qgis-project
description: Generate a QGIS project file (.qgz) with layers and styling
---

# QGIS Project Generator Skill

When the user invokes `/create-qgis-project`, generate a QGIS project file with proper layer configuration.

## Parameters
- **name**: Project name (required)
- **layers**: Comma-separated list of layer paths (required)
- **crs**: Project CRS (default: EPSG:4326)
- **output**: Output .qgz file path (optional)

## Features

### Layer Configuration
- Automatic layer ordering (polygons bottom, points top)
- CRS matching and transformation
- Attribute table configuration

### Styling
- Auto-generate styles based on geometry type
- Categorized styling for categorical attributes
- Graduated styling for numeric attributes

### Project Settings
- Set project extent to layer bounds
- Configure default map units
- Add basemap layers (OSM, satellite)

## Implementation Notes

Since QGIS project files are XML-based, this skill will:
1. Create a valid QGIS project XML structure
2. Add layer definitions with proper datasource paths
3. Include basic SLD/QML styling
4. Save as .qgz (compressed) or .qgs (uncompressed)

## Example Usage
```
/create-qgis-project name=Peru_Fires layers=fires.geojson,admin.shp
/create-qgis-project name=Analysis layers=data/*.geojson crs=EPSG:32718
```

## Output
- QGIS project file (.qgz or .qgs)
- Summary of layers added
- Instructions for opening in QGIS
