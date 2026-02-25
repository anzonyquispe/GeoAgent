---
name: validate-geojson
description: Validate and analyze GeoJSON files for correctness and quality
---

# GeoJSON Validator Skill

When the user invokes `/validate-geojson`, perform a comprehensive validation of GeoJSON files.

## Parameters
- **file_path**: Path to the GeoJSON file (required)
- **fix**: If "true", attempt to fix common issues (optional)

## Validation Checks

1. **Structure Validation**:
   - Valid JSON syntax
   - Required GeoJSON properties (type, features/geometry)
   - Feature collection vs single feature

2. **Geometry Validation**:
   - Valid geometry types (Point, LineString, Polygon, etc.)
   - Coordinate validity (within valid ranges)
   - Polygon ring closure
   - No self-intersections

3. **CRS Check**:
   - Check for CRS specification
   - Warn if non-WGS84 coordinates detected

4. **Data Quality**:
   - Null geometries
   - Empty geometries
   - Duplicate features
   - Property consistency across features

## Output Report
Generate a validation report with:
- Summary statistics (feature count, geometry types)
- List of errors found
- List of warnings
- Recommendations for fixing issues

## Example Usage
```
/validate-geojson data/boundaries.geojson
/validate-geojson data/points.geojson fix=true
```
