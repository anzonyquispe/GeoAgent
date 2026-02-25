"""
Municipality-level geospatial tools for Peru using GADM Level-3 boundaries.

This module provides functions to download and work with district-level
(municipality) administrative boundaries for Peru.

GADM Peru Levels:
- Level 1: 26 Regions/Departments (GID_1, NAME_1)
- Level 2: ~196 Provinces (GID_2, NAME_2)
- Level 3: ~1,874 Districts/Municipalities (GID_3, NAME_3)
"""

import geopandas as gpd
import pandas as pd
from typing import Literal, Optional, Dict, List


def download_gadm_boundaries(
    iso3: str = "PER",
    level: int = 3
) -> gpd.GeoDataFrame:
    """
    Download GADM administrative boundaries at specified level.

    Parameters
    ----------
    iso3 : str
        ISO3 country code (default: "PER" for Peru).
    level : int
        Administrative level (1=regions, 2=provinces, 3=districts).
        Default is 3 for municipality-level analysis.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame containing administrative boundaries.

        For Peru Level-3, includes columns:
        - GID_3, NAME_3: District ID and name
        - GID_2, NAME_2: Province ID and name
        - GID_1, NAME_1: Region ID and name
        - geometry: MultiPolygon boundaries

    Example
    -------
    >>> districts = download_gadm_boundaries("PER", level=3)
    >>> print(len(districts))  # ~1,874 districts
    """
    if level not in [1, 2, 3]:
        raise ValueError("level must be 1, 2, or 3")

    url = f"https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{iso3}_{level}.json"
    gdf = gpd.read_file(url)
    return gdf


def download_peru_districts() -> gpd.GeoDataFrame:
    """
    Download Peru district-level (Level-3) boundaries.

    Convenience wrapper for download_gadm_boundaries(iso3="PER", level=3).

    Returns
    -------
    gpd.GeoDataFrame
        ~1,874 district boundaries with hierarchical admin info.
    """
    return download_gadm_boundaries("PER", level=3)


def intersect_and_collapse_municipality(
    points_gdf: gpd.GeoDataFrame,
    boundaries_gdf: gpd.GeoDataFrame,
    id_col: str = "GID_3",
    level: Literal["year", "year_month"] = "year",
    agg_extra: Optional[Dict[str, str]] = None,
    keep_attrs: Optional[List[str]] = None,
) -> gpd.GeoDataFrame:
    """
    Spatial join point data with municipality boundaries and aggregate.

    Parameters
    ----------
    points_gdf : gpd.GeoDataFrame
        Point data (e.g., fire detections). Must contain 'year' and
        optionally 'month' columns, plus a geometry column.
    boundaries_gdf : gpd.GeoDataFrame
        Municipality (district) polygons. Must contain an ID column
        (default 'GID_3') and geometry.
    id_col : str
        Municipality identifier column in boundaries_gdf.
        Default 'GID_3' for GADM Level-3 districts.
    level : 'year' or 'year_month'
        Temporal aggregation level.
    agg_extra : dict, optional
        Extra aggregations on numeric fields, e.g., {'frp': 'sum'}.
    keep_attrs : list[str], optional
        Boundary columns to preserve (e.g., ['NAME_3', 'NAME_2', 'NAME_1']).

    Returns
    -------
    gpd.GeoDataFrame
        Aggregated data by municipality with columns:
        - [id_col]: Municipality ID
        - n_fires: Count of points
        - year, [month]: Time keys
        - [keep_attrs]: Preserved boundary attributes
        - geometry: Municipality polygon

    Example
    -------
    >>> fires = analyze_fires_data(2024)
    >>> districts = download_peru_districts()
    >>> result = intersect_and_collapse_municipality(
    ...     fires, districts,
    ...     keep_attrs=['NAME_3', 'NAME_2', 'NAME_1']
    ... )
    """
    if keep_attrs is None:
        keep_attrs = ["NAME_3", "NAME_2", "NAME_1"]

    if points_gdf.empty:
        base = boundaries_gdf[[id_col]].drop_duplicates().copy()
        return base.assign(n_fires=0)

    # Ensure common CRS
    if boundaries_gdf.crs is None:
        raise ValueError("Boundaries have no CRS. Set to EPSG:4326 or appropriate CRS.")
    if points_gdf.crs is None:
        raise ValueError("Points have no CRS. Ensure data was properly prepared.")

    if boundaries_gdf.crs.to_string() != points_gdf.crs.to_string():
        points = points_gdf.to_crs(boundaries_gdf.crs)
    else:
        points = points_gdf

    # Prepare columns for spatial join
    join_cols = [id_col, boundaries_gdf.geometry.name]
    for attr in keep_attrs:
        if attr in boundaries_gdf.columns and attr not in join_cols:
            join_cols.append(attr)

    # Spatial join: point within polygon
    joined = gpd.sjoin(
        points,
        boundaries_gdf[join_cols],
        how="inner",
        predicate="within"
    )

    # Grouping keys
    keys = [id_col]
    if level == "year_month":
        keys += ["year", "month"]
    else:
        keys += ["year"]

    # Count points + extra aggregations
    agg_dict = {"geometry": "count"}
    if agg_extra:
        agg_dict.update(agg_extra)

    grp = joined.groupby(keys, dropna=False).agg(agg_dict).reset_index()
    grp = grp.rename(columns={"geometry": "n_fires"})

    # Attach boundary attributes
    if keep_attrs:
        attrs = joined[[id_col] + keep_attrs].drop_duplicates(subset=[id_col])
        grp = grp.merge(attrs, on=id_col, how="left")

    # Ensure ints for time keys
    if "year" in grp.columns:
        grp["year"] = grp["year"].astype("Int64")
    if "month" in grp.columns:
        grp["month"] = grp["month"].astype("Int64")

    # Sort
    sort_cols = [c for c in [id_col, "year", "month"] if c in grp.columns]
    grp = grp.sort_values(sort_cols).reset_index(drop=True)

    # Merge with boundary geometries
    result = gpd.GeoDataFrame(
        boundaries_gdf.merge(grp, on=id_col, suffixes=('', '_dup'))
    )

    # Drop duplicate columns
    result = result[[c for c in result.columns if not c.endswith('_dup')]]

    return result


def aggregate_points_by_district(
    points_gdf: gpd.GeoDataFrame,
    value_cols: List[str],
    agg_funcs: Dict[str, str],
    boundaries_gdf: Optional[gpd.GeoDataFrame] = None,
) -> gpd.GeoDataFrame:
    """
    Generic point-to-polygon aggregation at district level.

    Parameters
    ----------
    points_gdf : gpd.GeoDataFrame
        Point data to aggregate.
    value_cols : list[str]
        Columns to aggregate.
    agg_funcs : dict[str, str]
        Aggregation functions per column, e.g., {'value': 'sum', 'count': 'mean'}.
    boundaries_gdf : gpd.GeoDataFrame, optional
        District boundaries. If None, downloads Peru Level-3.

    Returns
    -------
    gpd.GeoDataFrame
        Aggregated values by district.
    """
    if boundaries_gdf is None:
        boundaries_gdf = download_peru_districts()

    # Ensure CRS match
    if points_gdf.crs != boundaries_gdf.crs:
        points_gdf = points_gdf.to_crs(boundaries_gdf.crs)

    # Spatial join
    joined = gpd.sjoin(
        points_gdf,
        boundaries_gdf[['GID_3', 'NAME_3', 'NAME_2', 'NAME_1', 'geometry']],
        how="inner",
        predicate="within"
    )

    # Aggregate
    agg_dict = {col: agg_funcs.get(col, 'sum') for col in value_cols if col in joined.columns}
    agg_dict['geometry'] = 'count'

    result = joined.groupby('GID_3').agg(agg_dict).reset_index()
    result = result.rename(columns={'geometry': 'n_points'})

    # Merge back with boundaries
    return boundaries_gdf.merge(result, on='GID_3', how='left')


def get_district_hierarchy(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Extract district-province-region hierarchy from GADM Level-3 data.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GADM Level-3 boundaries.

    Returns
    -------
    pd.DataFrame
        Hierarchy table with columns:
        GID_3, NAME_3, GID_2, NAME_2, GID_1, NAME_1
    """
    cols = ['GID_3', 'NAME_3', 'GID_2', 'NAME_2', 'GID_1', 'NAME_1']
    available = [c for c in cols if c in gdf.columns]
    return gdf[available].drop_duplicates().reset_index(drop=True)
