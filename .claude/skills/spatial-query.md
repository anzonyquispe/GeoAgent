---
name: spatial-query
description: Execute spatial queries on geospatial datasets using natural language
---

# Spatial Query Skill

When the user invokes `/spatial-query`, translate natural language queries into geospatial operations.

## Supported Query Types

### 1. Point-in-Polygon Queries
- "Which region contains point X, Y?"
- "Find all points within polygon Z"

### 2. Distance Queries
- "Find all features within X km of location Y"
- "What is the distance between A and B?"

### 3. Intersection Queries
- "Which features intersect with layer X?"
- "Find overlapping areas between A and B"

### 4. Aggregation Queries
- "Count features by region"
- "Sum attribute X grouped by region Y"

## Implementation Steps

1. **Parse the query** to identify:
   - Operation type (contains, intersects, within, buffer, etc.)
   - Input layers/datasets
   - Parameters (distances, coordinates, attribute names)

2. **Load required data**:
   - Identify and load necessary datasets
   - Ensure CRS compatibility

3. **Execute the operation**:
   - Use GeoPandas spatial operations
   - Handle edge cases and errors gracefully

4. **Return results**:
   - Format output appropriately (table, GeoJSON, summary)
   - Include relevant statistics

## Example Usage
```
/spatial-query Find all fires within 50km of Lima
/spatial-query Count fires by department for 2023
/spatial-query Which regions have more than 1000 fires?
```
