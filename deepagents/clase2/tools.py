import pandas as pd
from datetime import date
from pathlib import Path
import tempfile
import os

# Shared state for passing data between tools within a session
_SESSION_DATA = {}

def download_viirs_snpp_peru(year: int) -> str:
    """
    Download NASA FIRMS per-country VIIRS-SNPP fires for Peru for a given year.

    Parameters
    ----------
    year : int
        Year to fetch (VIIRS-SNPP is available from 2012 to current year).

    Returns
    -------
    str
        A message confirming the download with the number of fire detections.
    """
    current_year = date.today().year
    if not isinstance(year, int):
        raise TypeError("year must be an integer, e.g., 2013")
    if year < 2012 or year > current_year:
        raise ValueError(f"year must be between 2012 and {current_year}")

    url = f"https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{year}/viirs-snpp_{year}_Peru.csv"
    df = pd.read_csv(url)
    
    _SESSION_DATA["fires_raw"] = df
    _SESSION_DATA["fires_year"] = year
    
    return f"Downloaded {len(df)} fire detections for Peru in {year}."



import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import Literal, Optional, Dict, List

def fires_clean() -> str:
    """
    Convert the downloaded VIIRS fires data into a GeoDataFrame with geometry and temporal columns.
    
    Must be called after download_viirs_snpp_peru.

    Returns
    -------
    str
        A message confirming the cleaning with statistics.
    """
    if "fires_raw" not in _SESSION_DATA:
        raise ValueError("No fire data found. Call download_viirs_snpp_peru first.")
    
    df = _SESSION_DATA["fires_raw"].copy()
    lat_col, lon_col = "latitude", "longitude"
    acq_time_col, acq_date_col = "acq_time", "acq_date"
    
    # Coerce coordinates and drop invalid rows
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])

    # Parse datetime
    dt = pd.to_datetime(df[acq_date_col], errors="coerce", utc=False)
    df["event_dt"] = dt
    df["year"] = df["event_dt"].dt.year.astype("Int64")
    df["month"] = df["event_dt"].dt.month.astype("Int64")

    # Build geometry
    geom = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")
    
    _SESSION_DATA["fires_gdf"] = gdf
    
    return f"Cleaned {len(gdf)} fire points with geometry. Year range: {gdf['year'].min()}-{gdf['year'].max()}."


def download_ctry_shp() -> str:
    """
    Download Peru administrative boundary polygons (Level-1 departments) from GADM.

    Returns
    -------
    str
        A message confirming the download with the number of regions.
    """
    ctry = gpd.read_file(r"https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PER_1.json")
    _SESSION_DATA["peru_boundaries"] = ctry
    
    regions = ctry["NAME_1"].tolist()
    return f"Downloaded Peru boundaries with {len(ctry)} departments: {', '.join(regions[:5])}..."



def intersect_and_collapse_fires_peru(
    level: Literal["year", "year_month"] = "year",
) -> str:
    """
    Intersect fire points with Peru administrative polygons and aggregate fire counts.

    Must be called after fires_clean and download_ctry_shp.

    Parameters
    ----------
    level : 'year' or 'year_month'
        Aggregation level. Default 'year'. Use 'year_month' for monthly breakdown.

    Returns
    -------
    str
        A summary of fire counts by region.
    """
    if "fires_gdf" not in _SESSION_DATA:
        raise ValueError("No cleaned fire data. Call fires_clean first.")
    if "peru_boundaries" not in _SESSION_DATA:
        raise ValueError("No Peru boundaries. Call download_ctry_shp first.")
    
    fires_gdf = _SESSION_DATA["fires_gdf"]
    peru_gdf = _SESSION_DATA["peru_boundaries"]
    id_col = "NAME_1"
    
    if fires_gdf.empty:
        base = peru_gdf[[id_col]].drop_duplicates().copy()
        result = base.assign(n_fires=0)
        _SESSION_DATA["aggregated"] = gpd.GeoDataFrame(peru_gdf.merge(result, on=id_col))
        return "No fires found in the dataset."

    # Spatial join
    joined = gpd.sjoin(fires_gdf, peru_gdf[[id_col, peru_gdf.geometry.name]],
                       how="inner", predicate="within")

    # Grouping keys
    keys = [id_col]
    if level == "year_month":
        keys += ["year", "month"]
    else:
        keys += ["year"]

    # Aggregate
    grp = joined.groupby(keys, dropna=False).agg({"geometry": "count"}).reset_index()
    grp = grp.rename(columns={"geometry": "n_fires"})

    if "year" in grp.columns:
        grp["year"] = grp["year"].astype("Int64")
    if "month" in grp.columns:
        grp["month"] = grp["month"].astype("Int64")

    grpd = gpd.GeoDataFrame(peru_gdf.merge(grp, on=id_col))
    _SESSION_DATA["aggregated"] = grpd
    
    # Summary
    top_5 = grpd.nlargest(5, "n_fires")[[id_col, "n_fires"]]
    summary = "\n".join([f"  {row[id_col]}: {row['n_fires']} fires" for _, row in top_5.iterrows()])
    total = grpd["n_fires"].sum()
    
    return f"Aggregated {total} fires by {level}. Top 5 regions:\n{summary}"




import os
import io
import zipfile
from datetime import date
from typing import List, Optional, Tuple

import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium


def folium_choropleth_peru(
    out_html: str = "peru_viirs_fires.html",
) -> str:
    """
    Create and save an interactive choropleth map showing fire counts by region.

    Must be called after intersect_and_collapse_fires_peru.

    Parameters
    ----------
    out_html : str
        Output HTML file path (default: "peru_viirs_fires.html").

    Returns
    -------
    str
        A message confirming the map was saved with the file path.
    """
    if "aggregated" not in _SESSION_DATA:
        raise ValueError("No aggregated data. Call intersect_and_collapse_fires_peru first.")
    
    prov_counts_gdf = _SESSION_DATA["aggregated"]
    value_col = "n_fires"
    prov_id = "NAME_1"
    name_col = "NAME_1"
    
    # Center roughly on Peru
    m = folium.Map(location=[-9.2, -75.0], zoom_start=5, tiles="cartodbpositron")

    # Prepare choropleth
    chor = folium.Choropleth(
        geo_data=prov_counts_gdf.to_json(),
        data=prov_counts_gdf,
        columns=[prov_id, value_col],
        key_on=f"feature.properties.{prov_id}",
        fill_opacity=0.8,
        line_opacity=0.7,
        legend_name="VIIRS active fires (count)",
        highlight=True,
        nan_fill_opacity=0.2,
        bins=8,
    )
    chor.add_to(m)

    # Add interactive tooltip
    folium.GeoJson(
        prov_counts_gdf.to_json(),
        name="Provinces",
        style_function=lambda x: {"weight": 0.5, "color": "#555", "fillOpacity": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=[name_col, value_col],
            aliases=["Region", "Fires"],
            localize=True,
            sticky=False,
        ),
    ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(out_html)
    
    year = _SESSION_DATA.get("fires_year", "unknown")
    return f"Saved interactive map to '{out_html}' showing fire counts for Peru ({year})."