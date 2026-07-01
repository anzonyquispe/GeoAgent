#!/usr/bin/env python3
"""
Example 1: AI Agent Tools for Spatial Analysis
===============================================

This example demonstrates how to create AI agent tools that can
analyze geospatial data autonomously. The agent can:
- Download satellite fire data
- Aggregate by administrative boundaries
- Generate insights for public policy

Run time: ~30 seconds
"""

import sys
sys.path.insert(0, '/Users/anzony.quisperojas/Documents/GitHub/python/GeoAgent')

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

print("=" * 60)
print("EXAMPLE 1: AI Agent Tools for Fire Analysis")
print("=" * 60)

# ============================================================
# STEP 1: Define the Agent Tool
# ============================================================
print("\n[Step 1] Defining Agent Tool...")

def analyze_fires_tool(year: int, country: str = "PER") -> dict:
    """
    AI Agent Tool: Analyze fire data for a country.

    This function can be called by an LLM to analyze fires.
    The LLM decides WHEN and HOW to use this tool based on
    natural language queries like "What fires happened in Peru?"

    Parameters
    ----------
    year : int
        Year to analyze
    country : str
        ISO3 country code

    Returns
    -------
    dict
        Analysis results that the LLM can interpret
    """
    # Download fire data from NASA FIRMS
    url = f"https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{year}/viirs-snpp_{year}_Peru.csv"
    fires_df = pd.read_csv(url)

    # Convert to GeoDataFrame
    fires_df['geometry'] = [Point(xy) for xy in zip(fires_df['longitude'], fires_df['latitude'])]
    fires_gdf = gpd.GeoDataFrame(fires_df, geometry='geometry', crs="EPSG:4326")

    # Download admin boundaries (Level 1 for speed)
    boundaries = gpd.read_file("https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PER_1.json")

    # Spatial join
    joined = gpd.sjoin(fires_gdf, boundaries[['NAME_1', 'geometry']], predicate='within')

    # Aggregate
    result = joined.groupby('NAME_1').size().reset_index(name='fire_count')
    result = result.sort_values('fire_count', ascending=False)

    return {
        'total_fires': len(fires_df),
        'regions_affected': len(result),
        'top_5_regions': result.head(5).to_dict('records'),
        'year': year
    }

# ============================================================
# STEP 2: Simulate LLM Agent Interaction
# ============================================================
print("\n[Step 2] Simulating LLM Agent Interaction...")

# This is what happens when a user asks:
# "What regions in Peru had the most fires in 2024?"

user_query = "What regions in Peru had the most fires in 2024?"
print(f"\nUser Query: '{user_query}'")

print("\n[LLM Reasoning]")
print("  1. User wants fire data for Peru")
print("  2. Year specified: 2024")
print("  3. Need to use 'analyze_fires_tool'")
print("  4. Calling tool with parameters: year=2024, country='PER'")

# Agent calls the tool
result = analyze_fires_tool(year=2024, country="PER")

print("\n[Tool Result]")
print(f"  Total fires detected: {result['total_fires']:,}")
print(f"  Regions affected: {result['regions_affected']}")

print("\n[LLM Response Generation]")
print("-" * 40)
print(f"In 2024, Peru experienced {result['total_fires']:,} fire detections.")
print(f"The fires affected {result['regions_affected']} regions.")
print("\nTop 5 regions by fire count:")
for i, region in enumerate(result['top_5_regions'], 1):
    print(f"  {i}. {region['NAME_1']}: {region['fire_count']:,} fires")

# ============================================================
# STEP 3: Policy Insights
# ============================================================
print("\n" + "=" * 60)
print("PUBLIC POLICY INSIGHTS")
print("=" * 60)

top_region = result['top_5_regions'][0]
print(f"""
Based on this analysis, policymakers can:

1. RESOURCE ALLOCATION
   - Direct firefighting resources to {top_region['NAME_1']}
   - {top_region['fire_count']:,} fires = highest priority region

2. PREVENTION PROGRAMS
   - Target awareness campaigns in Amazon regions
   - Top 5 regions account for majority of fires

3. MONITORING
   - Increase satellite monitoring in hotspots
   - Real-time alerts for affected communities

4. LEGISLATION
   - Strengthen enforcement in high-fire regions
   - Review land-use policies in {top_region['NAME_1']}
""")

print("=" * 60)
print("Example completed successfully!")
print("=" * 60)
