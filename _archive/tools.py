import pandas as pd
from datetime import date
import geopandas as gpd
from shapely.geometry import Point
from typing import Literal, Optional, Dict, List
from langchain.tools import tool

def download_viirs_snpp_peru(year: int, save_path: str | None = None) -> tuple[pd.DataFrame, str]:
    """
    Download NASA FIRMS per-country VIIRS-SNPP fires for Peru for a given year.

    Parameters
    ----------
    year : int
        Year to fetch (VIIRS-SNPP is available from ~2012 onward).
    save_path : str | None
        If provided, saves the downloaded CSV to this path.

    Returns
    -------
    (df, url) : (pandas.DataFrame, str)
        The DataFrame with the fires and the exact URL used.

    Example
    -------
    df, url = download_viirs_snpp_peru(2013, "viirs-snpp_2013_Peru.csv")
    """
    # Basic sanity checks
    current_year = date.today().year
    if not isinstance(year, int):
        raise TypeError("year must be an integer, e.g., 2013")
    if year < 2012 or year > current_year:
        raise ValueError(f"year must be between 2012 and {current_year}")

    # URL pattern from your example
    url = f"https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{year}/viirs-snpp_{year}_Peru.csv"

    # Read directly with pandas
    df = pd.read_csv(url)

    return(df)


def fires_clean(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    acq_time_col: str = "acq_time",
    acq_date_col: str = "acq_date",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Convert raw VIIRS fires DataFrame into a GeoDataFrame and add year/month.

    Assumptions
    ----------
    - The input has columns:
      ['latitude','longitude','bright_ti4','scan','track','acq_date','acq_time',
       'satellite','instrument','confidence','version','bright_ti5','frp','daynight','type']
    - `acq_time` is a DATE string in the form 'YYYY-MM-DD' (per your example).
      If not parseable, we fall back to `acq_date`.

    Returns
    -------
    gdf : GeoDataFrame (EPSG:4326)
        Adds columns: 'event_dt' (Timestamp), 'year' (int), 'month' (int)
    """
    df = df.copy()

    # Coerce coordinates and drop invalid rows
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])

    # Parse datetime (prefer acq_time as per your format; fallback to acq_date)
    dt = pd.to_datetime(df[acq_time_col], errors="coerce", utc=False)
    if dt.isna().all() and acq_date_col in df.columns:
        dt = pd.to_datetime(df[acq_date_col], errors="coerce", utc=False)

    if dt.isna().all():
        raise ValueError("Could not parse dates from 'acq_time' or 'acq_date'.")

    df["event_dt"] = dt
    df["year"] = df["event_dt"].dt.year.astype("Int64")
    df["month"] = df["event_dt"].dt.month.astype("Int64")

    # Build geometry
    geom = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geom, crs=crs)

    return gdf

def download_ctry_shp(iso3: str = "PER") -> gpd.GeoDataFrame:
    """
    Download country shapefile from GADM database.

    Parameters
    ----------
    iso3 : str
        ISO3 country code (default: "PER" for Peru).

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame containing administrative boundaries.
    """
    ctry = gpd.read_file(r"https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PER_1.json")
    return ctry

def intersect_and_collapse_fires_peru(
    fires_gdf: gpd.GeoDataFrame,
    peru_lvl2_gdf: gpd.GeoDataFrame,
    id_col: str = "prov_id",
    level: Literal["year", "year_month"] = "year",
    agg_extra: Optional[Dict[str, str]] = None,
    keep_province_attrs: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Intersect fire points with Peru Level-2 polygons and collapse counts.

    Parameters
    ----------
    fires_gdf : GeoDataFrame
        Output of `fires_clean` (must contain 'year' and 'month' and a geometry).
    peru_lvl2_gdf : GeoDataFrame
        Peru polygons (e.g., GADM level-2). Must contain an ID column (default 'prov_id').
    id_col : str
        Province identifier column name in `peru_lvl2_gdf`.
    level : 'year' or 'year_month'
        Aggregation level. Default 'year'. If 'year_month', groups by (year, month).
    agg_extra : dict, optional
        Extra aggregations on numeric fields, e.g., {'frp': 'sum'} to sum FRP.
    keep_province_attrs : list[str], optional
        Extra province columns (e.g., ['province','region']) to include in the output.

    Returns
    -------
    df_out : pandas.DataFrame
        Columns include: [id_col], 'n_fires', and time keys ('year' [, 'month']).
        If `keep_province_attrs` provided, they are included (deduplicated merge).
    """
    if fires_gdf.empty:
        # Build empty skeleton with available province ids & time keys if desired
        base = peru_lvl2_gdf[[id_col]].drop_duplicates().copy()
        return base.assign(n_fires=0)

    # Ensure common CRS
    if peru_lvl2_gdf.crs is None:
        raise ValueError("Peru polygons have no CRS. Set to EPSG:4326 or appropriate CRS.")
    if fires_gdf.crs is None:
        raise ValueError("fires_gdf has no CRS. Ensure `fires_clean` was used or set CRS.")

    if peru_lvl2_gdf.crs.to_string() != fires_gdf.crs.to_string():
        fires = fires_gdf.to_crs(peru_lvl2_gdf.crs)
    else:
        fires = fires_gdf

    # Spatial join: point within polygon
    joined = gpd.sjoin(fires, peru_lvl2_gdf[[id_col, peru_lvl2_gdf.geometry.name] + ([] if not keep_province_attrs else keep_province_attrs)],
                       how="inner", predicate="within")

    # Grouping keys
    keys = [id_col]
    if level == "year_month":
        keys += ["year", "month"]
    else:
        keys += ["year"]

    # Count fires + extra aggregations
    agg_dict = {"geometry": "count"}  # we will rename to n_fires
    if agg_extra:
        agg_dict.update(agg_extra)

    grp = joined.groupby(keys, dropna=False).agg(agg_dict).reset_index()
    grp = grp.rename(columns={"geometry": "n_fires"})

    # Optionally attach province attrs (deduplicate first)
    if keep_province_attrs:
        attrs = joined[[id_col] + keep_province_attrs].drop_duplicates(subset=[id_col])
        grp = grp.merge(attrs, on=id_col, how="left")

    # Ensure ints for time keys
    if "year" in grp.columns:
        grp["year"] = grp["year"].astype("Int64")
    if "month" in grp.columns:
        grp["month"] = grp["month"].astype("Int64")

    # Sort nicely
    sort_cols = [c for c in [id_col, "year", "month"] if c in grp.columns]
    grp = grp.sort_values(sort_cols).reset_index(drop=True)

    # Merge with boundary data, ensuring NAME_1 is included
    grpd = gpd.GeoDataFrame(
        peru_lvl2_gdf.merge(grp, on=id_col, suffixes=('', '_dup'))
    )
    
    # Drop duplicate columns created by merge
    grpd = grpd[[c for c in grpd.columns if not c.endswith('_dup')]]
    
    return grpd


def process_peru_fires_complete(
    year: int,
    id_col: str = "GID_1",
    level: Literal["year", "year_month"] = "year",
    agg_extra: Optional[Dict[str, str]] = None,
    keep_province_attrs: Optional[List[str]] = None,
) -> gpd.GeoDataFrame:
    """Implementation of complete pipeline without @tool decorator."""
    # Download fires data (function returns just DataFrame now)
    fires_df = download_viirs_snpp_peru(year)
    fires_gdf = fires_clean(fires_df)
    peru_gdf = download_ctry_shp()
    result = intersect_and_collapse_fires_peru(
        fires_gdf=fires_gdf,
        peru_lvl2_gdf=peru_gdf,
        id_col=id_col,
        level=level,
        agg_extra=agg_extra,
        keep_province_attrs=keep_province_attrs,
    )
    return result


@tool
def get_peru_fires(
    year: int,
    id_col: str = "GID_1",
    level: Literal["year", "year_month"] = "year",
    agg_extra: Optional[Dict[str, str]] = None,
    keep_province_attrs: Optional[List[str]] = None,
) -> str:
    """
    Get fire data for Peru in a specific year and return as a formatted table.

    This function responds to questions like:
    "What fires happened in Peru in year XXX?"
    
    This function combines all four operations:
    1. Downloads VIIRS-SNPP fire data for Peru for the specified year
    2. Cleans and converts fires to GeoDataFrame with temporal attributes
    3. Downloads Peru administrative boundaries from GADM
    4. Spatially joins fires with boundaries and aggregates by region/time

    Parameters
    ----------
    year : int
        Year to fetch fire data (VIIRS-SNPP available from ~2012 onward).
    id_col : str
        Administrative unit identifier column in boundary data
        (default: "GID_1").
    level : 'year' or 'year_month'
        Temporal aggregation level. Default 'year'.
        If 'year_month', groups by (year, month).
    agg_extra : dict, optional
        Extra aggregations on numeric fields, e.g., {'frp': 'sum'}.
    keep_province_attrs : list[str], optional
        Extra boundary columns to include in output
        (e.g., ['NAME_1', 'TYPE_1']).

    Returns
    -------
    str
        A formatted table string showing fire counts by region/province.

    Example
    -------
    # Get annual fire counts by province for 2023
    result = get_peru_fires.invoke({"year": 2023, "level": "year"})
    
    # Get monthly fire counts with FRP sum
    result = get_peru_fires.invoke({
        "year": 2023,
        "level": "year_month",
        "agg_extra": {'frp': 'sum'},
        "keep_province_attrs": ['NAME_1']
    })
    """
    df = process_peru_fires_complete(
        year=year,
        id_col=id_col,
        level=level,
        agg_extra=agg_extra,
        keep_province_attrs=keep_province_attrs,
    )

    # Select relevant columns and sort by fire count
    result_df = df[['NAME_1', 'year', 'n_fires']].copy()
    result_df = result_df.sort_values(
        'n_fires', ascending=False
    ).reset_index(drop=True)
    
    # Format as a readable table string
    table_string = f"\nFire counts in Peru for {year}:\n\n"
    table_string += result_df.to_string(index=False)
    table_string += f"\n\nTotal fires: {result_df['n_fires'].sum()}"
    
    return table_string
