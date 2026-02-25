"""
Global Forest Watch (Hansen) data analysis tools.

This module provides functions to download and analyze forest cover data
from the Global Forest Change dataset (Hansen et al.) at municipality level.

Data Source: https://glad.earthengine.app/view/global-forest-change
Hansen et al. (2013) Global Forest Change 2000-2024

Layers available:
- treecover2000: Tree canopy cover for year 2000 (%)
- lossyear: Year of forest loss (1-24 = 2001-2024)
- gain: Forest gain 2000-2012 (binary)
- datamask: Data mask (0=no data, 1=mapped land, 2=water)
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import requests
import tempfile
import warnings

# Hansen GFC 2024 tile configuration for Peru
# Peru spans approximately -0.04 to -18.35 latitude, -81.33 to -68.65 longitude
PERU_TILES = [
    "00N_080W",  # Northern Peru (border with Ecuador/Colombia)
    "00N_070W",  # Northern Peru
    "10S_080W",  # Central Peru (Lima, Junin)
    "10S_070W",  # Central-Eastern Peru (Ucayali)
    "20S_080W",  # Southern Peru (Arequipa)
    "20S_070W",  # Southern Peru (Puno, Madre de Dios)
]

GFC_BASE_URL = "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12"

# Try to import rasterio, but provide fallback
try:
    import rasterio
    from rasterio.mask import mask as rasterio_mask
    from rasterio.merge import merge as rasterio_merge
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    warnings.warn(
        "rasterio not available. Forest raster analysis will be limited. "
        "Install with: pip install rasterio"
    )


def check_rasterio():
    """Check if rasterio is available for raster operations."""
    if not RASTERIO_AVAILABLE:
        raise ImportError(
            "rasterio is required for forest raster analysis. "
            "Install with: pip install rasterio"
        )


def download_hansen_tile(
    tile: str,
    layer: str = "treecover2000",
    cache_dir: str = "./gfc_cache"
) -> Path:
    """
    Download a Hansen Global Forest Change tile.

    Parameters
    ----------
    tile : str
        Tile ID (e.g., "10S_080W").
    layer : str
        One of "treecover2000", "lossyear", "gain", "datamask".
    cache_dir : str
        Local cache directory for downloaded tiles.

    Returns
    -------
    Path
        Path to downloaded GeoTIFF file.

    Example
    -------
    >>> path = download_hansen_tile("10S_080W", "lossyear")
    >>> print(path)
    PosixPath('./gfc_cache/Hansen_GFC-2024-v1.12_lossyear_10S_080W.tif')
    """
    valid_layers = ["treecover2000", "lossyear", "gain", "datamask", "first", "last"]
    if layer not in valid_layers:
        raise ValueError(f"layer must be one of {valid_layers}")

    filename = f"Hansen_GFC-2024-v1.12_{layer}_{tile}.tif"
    url = f"{GFC_BASE_URL}/{filename}"

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    local_path = cache_path / filename

    if not local_path.exists():
        print(f"Downloading {filename}...")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded to {local_path}")

    return local_path


def download_peru_hansen_tiles(
    layers: List[str] = None,
    cache_dir: str = "./gfc_cache"
) -> Dict[str, List[Path]]:
    """
    Download all Hansen tiles for Peru.

    Parameters
    ----------
    layers : list[str], optional
        Layers to download. Default: ["treecover2000", "lossyear", "gain"]
    cache_dir : str
        Cache directory for tiles.

    Returns
    -------
    dict[str, list[Path]]
        Dictionary mapping layer names to lists of tile paths.
    """
    if layers is None:
        layers = ["treecover2000", "lossyear", "gain"]

    result = {}
    for layer in layers:
        result[layer] = []
        for tile in PERU_TILES:
            try:
                path = download_hansen_tile(tile, layer, cache_dir)
                result[layer].append(path)
            except Exception as e:
                print(f"Warning: Could not download {layer} for tile {tile}: {e}")

    return result


def calculate_forest_stats_for_polygon(
    geometry,
    treecover_path: Path,
    lossyear_path: Path,
    gain_path: Path,
    threshold: int = 30
) -> Dict:
    """
    Calculate forest statistics for a single polygon.

    Parameters
    ----------
    geometry : shapely.geometry
        Polygon geometry to analyze.
    treecover_path : Path
        Path to treecover2000 raster.
    lossyear_path : Path
        Path to lossyear raster.
    gain_path : Path
        Path to gain raster.
    threshold : int
        Minimum tree cover percentage to consider as forest.

    Returns
    -------
    dict
        Forest statistics including area, loss by year, and gain.
    """
    check_rasterio()

    geom = [geometry]
    stats = {
        'forest_area_2000_ha': 0,
        'loss_total_ha': 0,
        'gain_area_ha': 0,
        'net_change_ha': 0,
        'loss_by_year': {}
    }

    try:
        # Tree cover 2000
        with rasterio.open(treecover_path) as src:
            out_image, out_transform = rasterio_mask(src, geom, crop=True, nodata=0)
            pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000
            forest_pixels = np.sum(out_image[0] >= threshold)
            stats['forest_area_2000_ha'] = forest_pixels * pixel_area_ha

        # Loss by year
        with rasterio.open(lossyear_path) as src:
            out_image, _ = rasterio_mask(src, geom, crop=True, nodata=0)
            for year_code in range(1, 25):  # 1-24 = 2001-2024
                loss_pixels = np.sum(out_image[0] == year_code)
                loss_ha = loss_pixels * pixel_area_ha
                stats['loss_by_year'][2000 + year_code] = loss_ha
            stats['loss_total_ha'] = sum(stats['loss_by_year'].values())

        # Gain 2000-2012
        with rasterio.open(gain_path) as src:
            out_image, _ = rasterio_mask(src, geom, crop=True, nodata=0)
            gain_pixels = np.sum(out_image[0] == 1)
            stats['gain_area_ha'] = gain_pixels * pixel_area_ha

        stats['net_change_ha'] = stats['gain_area_ha'] - stats['loss_total_ha']

    except Exception as e:
        print(f"Warning: Error processing polygon: {e}")

    return stats


def calculate_forest_stats_by_municipality(
    boundaries_gdf: gpd.GeoDataFrame,
    treecover_path: Path,
    lossyear_path: Path,
    gain_path: Path,
    threshold: int = 30,
    id_col: str = "GID_3",
    name_cols: List[str] = None
) -> gpd.GeoDataFrame:
    """
    Calculate forest statistics for each municipality.

    Parameters
    ----------
    boundaries_gdf : gpd.GeoDataFrame
        Municipality boundaries (GADM Level-3).
    treecover_path : Path
        Path to treecover2000 raster (or merged VRT).
    lossyear_path : Path
        Path to lossyear raster.
    gain_path : Path
        Path to gain raster.
    threshold : int
        Minimum tree cover % to consider as forest. Default 30%.
    id_col : str
        Municipality ID column. Default "GID_3".
    name_cols : list[str], optional
        Name columns to preserve. Default ["NAME_3", "NAME_2", "NAME_1"].

    Returns
    -------
    gpd.GeoDataFrame
        Boundaries with forest statistics columns:
        - forest_area_2000_ha: Forest area in year 2000
        - loss_total_ha: Total forest loss 2001-2024
        - loss_by_year: Dict of annual loss
        - gain_area_ha: Forest gain 2000-2012
        - net_change_ha: gain - loss
    """
    check_rasterio()

    if name_cols is None:
        name_cols = ["NAME_3", "NAME_2", "NAME_1"]

    results = []
    total = len(boundaries_gdf)

    for idx, row in boundaries_gdf.iterrows():
        if idx % 100 == 0:
            print(f"Processing municipality {idx + 1}/{total}...")

        stats = calculate_forest_stats_for_polygon(
            row.geometry,
            treecover_path,
            lossyear_path,
            gain_path,
            threshold
        )

        result_row = {id_col: row[id_col]}
        for col in name_cols:
            if col in row:
                result_row[col] = row[col]
        result_row.update(stats)
        results.append(result_row)

    result_df = pd.DataFrame(results)
    return boundaries_gdf.merge(result_df, on=id_col)


def get_peru_forest_stats(
    year_range: Tuple[int, int] = (2001, 2024),
    threshold: int = 30,
    cache_dir: str = "./gfc_cache",
    sample_n: Optional[int] = None
) -> gpd.GeoDataFrame:
    """
    Complete pipeline to get forest statistics for Peru municipalities.

    This is the main entry point for forest analysis, analogous to
    `process_peru_fires_complete` for fire analysis.

    Parameters
    ----------
    year_range : tuple[int, int]
        Range of years for loss analysis.
    threshold : int
        Minimum tree cover % to consider as forest.
    cache_dir : str
        Directory to cache downloaded tiles.
    sample_n : int, optional
        If provided, only analyze first N municipalities (for testing).

    Returns
    -------
    gpd.GeoDataFrame
        Municipality-level forest statistics.

    Example
    -------
    >>> forest_data = get_peru_forest_stats(threshold=25)
    >>> top_loss = forest_data.nlargest(10, 'loss_total_ha')
    >>> print(top_loss[['NAME_3', 'NAME_1', 'loss_total_ha']])
    """
    from municipality_tools import download_peru_districts

    print("Downloading Peru district boundaries...")
    boundaries = download_peru_districts()

    if sample_n:
        boundaries = boundaries.head(sample_n)

    print("Downloading Hansen GFC tiles for Peru...")
    tiles = download_peru_hansen_tiles(
        layers=["treecover2000", "lossyear", "gain"],
        cache_dir=cache_dir
    )

    # For now, use first tile (would need VRT merge for full analysis)
    # This is a simplified version - full implementation would merge tiles
    if not tiles.get("treecover2000"):
        raise ValueError("No treecover tiles downloaded")

    print("Calculating forest statistics by municipality...")
    result = calculate_forest_stats_by_municipality(
        boundaries_gdf=boundaries,
        treecover_path=tiles["treecover2000"][0],
        lossyear_path=tiles["lossyear"][0],
        gain_path=tiles["gain"][0],
        threshold=threshold
    )

    return result


def summarize_forest_loss_by_region(
    forest_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Aggregate forest loss statistics by region (Level-1).

    Parameters
    ----------
    forest_gdf : gpd.GeoDataFrame
        Municipality-level forest data.

    Returns
    -------
    pd.DataFrame
        Regional forest loss summary.
    """
    agg = forest_gdf.groupby('NAME_1').agg({
        'forest_area_2000_ha': 'sum',
        'loss_total_ha': 'sum',
        'gain_area_ha': 'sum',
        'net_change_ha': 'sum'
    }).reset_index()

    agg = agg.sort_values('loss_total_ha', ascending=False)
    return agg


def get_annual_loss_time_series(
    forest_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Extract annual forest loss time series from municipality data.

    Parameters
    ----------
    forest_gdf : gpd.GeoDataFrame
        Municipality data with loss_by_year column.

    Returns
    -------
    pd.DataFrame
        Annual loss totals with columns: year, loss_ha
    """
    yearly_loss = {}

    for _, row in forest_gdf.iterrows():
        loss_dict = row.get('loss_by_year', {})
        if isinstance(loss_dict, dict):
            for year, loss in loss_dict.items():
                yearly_loss[year] = yearly_loss.get(year, 0) + loss

    df = pd.DataFrame([
        {'year': year, 'loss_ha': loss}
        for year, loss in sorted(yearly_loss.items())
    ])

    return df
