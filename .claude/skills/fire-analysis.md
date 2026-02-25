---
name: fire-analysis
description: Analyze fire data for a specific country and year using NASA VIIRS data
---

# Fire Analysis Skill

When the user invokes `/fire-analysis`, perform the following steps:

## Parameters
Parse the user's input for:
- **country**: The country to analyze (default: Peru)
- **year**: The year to fetch data for (required)
- **aggregation**: "year" or "year_month" (default: "year")

## Steps

1. **Load the fire data**:
   - Use the `download_viirs_snpp_peru()` function from `tools.py`
   - Clean the data using `fires_clean()`

2. **Load administrative boundaries**:
   - Use `download_ctry_shp()` to get GADM boundaries

3. **Perform spatial analysis**:
   - Use `intersect_and_collapse_fires_peru()` to aggregate fires by region
   - Include FRP (Fire Radiative Power) sum in aggregations

4. **Generate output**:
   - Create a summary table showing fire counts by region
   - Identify the top 5 regions with most fires
   - Calculate total fires for the period

5. **Optional visualization**:
   - If requested, create a Folium choropleth map using `folium_choropleth_peru()`

## Example Usage
```
/fire-analysis 2023
/fire-analysis Peru 2022 year_month
```

## Output Format
Provide results as a formatted table with:
- Region name
- Fire count
- Total FRP
- Percentage of total fires
