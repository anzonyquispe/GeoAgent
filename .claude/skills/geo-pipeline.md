---
name: geo-pipeline
description: Run a complete geospatial data processing pipeline
allowed_tools:
  - Bash
  - Read
  - Write
  - Glob
---

# Geospatial Pipeline Skill

When the user invokes `/geo-pipeline`, execute a complete data processing workflow.

## Pipeline Stages

### Stage 1: Data Ingestion
- Scan input directory for geospatial files
- Validate file formats and structures
- Log any issues found

### Stage 2: Data Cleaning
- Remove null geometries
- Fix invalid geometries (buffer(0) trick)
- Standardize CRS to EPSG:4326
- Clean attribute names (lowercase, no spaces)

### Stage 3: Processing
- Execute specified spatial operations
- Generate derived attributes
- Perform aggregations

### Stage 4: Export
- Export processed data to specified formats
- Generate metadata files
- Create processing log

## Configuration

The pipeline can be configured via a YAML file:

```yaml
pipeline:
  input_dir: ./data/raw
  output_dir: ./data/processed
  operations:
    - type: buffer
      distance: 1000
    - type: spatial_join
      right_layer: admin_boundaries.geojson
  output_format: GeoJSON
```

## Example Usage
```
/geo-pipeline config=pipeline.yaml
/geo-pipeline input=data/raw output=data/processed
```
