#!/usr/bin/env python3
"""
Run GeoAgent Analysis - Fire and Forest Analysis for Peru

This script demonstrates the OpenSourceGeoAgent workflow:
1. Download fire data from NASA FIRMS
2. Aggregate at municipality level (GADM Level-3)
3. Create choropleth maps
4. Generate Marp presentation
"""

import sys
sys.path.insert(0, '/Users/anzony.quisperojas/Documents/GitHub/python/GeoAgent')

from pathlib import Path
from datetime import date

# Import local modules
from tools import download_viirs_snpp_peru, fires_clean
from municipality_tools import download_peru_districts, intersect_and_collapse_municipality

print("=" * 60)
print("GeoAgent - Peru Fire Analysis at Municipality Level")
print("=" * 60)

# Configuration
YEAR = 2024  # Year to analyze
OUTPUT_DIR = Path("/Users/anzony.quisperojas/Documents/GitHub/python/GeoAgent/output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Step 1: Download fire data
print(f"\n[1/5] Downloading fire data for {YEAR}...")
try:
    fires_df = download_viirs_snpp_peru(YEAR)
    print(f"      Downloaded {len(fires_df):,} fire detections")
except Exception as e:
    print(f"      Error downloading {YEAR}, trying 2023...")
    YEAR = 2023
    fires_df = download_viirs_snpp_peru(YEAR)
    print(f"      Downloaded {len(fires_df):,} fire detections for {YEAR}")

# Step 2: Clean and convert to GeoDataFrame
print("\n[2/5] Cleaning fire data...")
fires_gdf = fires_clean(fires_df)
print(f"      Created GeoDataFrame with {len(fires_gdf)} points")
print(f"      CRS: {fires_gdf.crs}")

# Step 3: Download municipality boundaries
print("\n[3/5] Downloading Peru district boundaries (GADM Level-3)...")
districts = download_peru_districts()
print(f"      Downloaded {len(districts):,} districts")

# Step 4: Aggregate fires by municipality
print("\n[4/5] Aggregating fires by municipality...")
result = intersect_and_collapse_municipality(
    points_gdf=fires_gdf,
    boundaries_gdf=districts,
    id_col="GID_3",
    level="year",
    agg_extra={'frp': 'sum'},
    keep_attrs=["NAME_3", "NAME_2", "NAME_1"]
)

# Calculate stats
total_fires = result['n_fires'].sum() if 'n_fires' in result.columns else 0
affected = len(result[result.get('n_fires', 0) > 0])
print(f"      Total fires: {total_fires:,}")
print(f"      Municipalities affected: {affected:,}")

# Step 5: Create choropleth map
print("\n[5/5] Creating choropleth map...")
import folium

m = folium.Map(location=[-9.2, -75.0], zoom_start=5, tiles="cartodbpositron")

# Add choropleth
folium.Choropleth(
    geo_data=result.to_json(),
    data=result,
    columns=['GID_3', 'n_fires'],
    key_on='feature.properties.GID_3',
    fill_color='YlOrRd',
    fill_opacity=0.8,
    line_opacity=0.5,
    legend_name=f'Fire Count ({YEAR})',
    nan_fill_color='white',
).add_to(m)

# Add tooltips
folium.GeoJson(
    result.to_json(),
    style_function=lambda x: {'fillOpacity': 0, 'weight': 0.5, 'color': 'gray'},
    tooltip=folium.GeoJsonTooltip(
        fields=['NAME_3', 'NAME_1', 'n_fires'],
        aliases=['District', 'Region', 'Fires'],
        localize=True,
    ),
).add_to(m)

map_path = OUTPUT_DIR / f"peru_fires_{YEAR}_municipalities.html"
m.save(str(map_path))
print(f"      Map saved to: {map_path}")

# Print top 20 municipalities
print("\n" + "=" * 60)
print(f"TOP 20 MUNICIPALITIES BY FIRE COUNT ({YEAR})")
print("=" * 60)

if 'n_fires' in result.columns:
    top20 = result.nlargest(20, 'n_fires')[['NAME_3', 'NAME_2', 'NAME_1', 'n_fires', 'frp']]
    for i, row in enumerate(top20.itertuples(), 1):
        frp = f"{row.frp:,.0f}" if hasattr(row, 'frp') and row.frp else "N/A"
        print(f"{i:2}. {row.NAME_3[:25]:<25} | {row.NAME_1[:15]:<15} | {row.n_fires:>6,} fires | FRP: {frp}")

# Regional summary
print("\n" + "=" * 60)
print("FIRE COUNT BY REGION")
print("=" * 60)

regional = result.groupby('NAME_1').agg({
    'n_fires': 'sum'
}).reset_index().sort_values('n_fires', ascending=False)

for i, row in enumerate(regional.itertuples(), 1):
    print(f"{i:2}. {row.NAME_1:<25} | {row.n_fires:>8,} fires")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
print(f"\nOutputs saved to: {OUTPUT_DIR}")
print(f"  - Map: peru_fires_{YEAR}_municipalities.html")
print(f"\nTo view the map, open it in your browser:")
print(f"  open {map_path}")
