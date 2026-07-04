# Environment Setup

Two options: **conda** (recommended for geospatial packages) or **pip** directly from `pyproject.toml`.

---

## Option A — Conda (recommended)

Geospatial libraries like `rasterio`, `geopandas`, and `xarray` have complex binary dependencies that conda resolves automatically.

```bash
# 1. Create the environment (Python 3.12)
conda create -n geoagent python=3.12 -y
conda activate geoagent

# 2. Install geospatial stack from conda-forge
conda install -c conda-forge \
    geopandas shapely rasterio rioxarray \
    xarray netCDF4 affine rasterstats h5py \
    contextily folium dask-geopandas pyarrow \
    duckdb geowombat \
    matplotlib numpy pandas \
    ipykernel jupyter -y

# 3. Install remaining packages via pip
pip install \
    lonboard \
    python-dotenv requests rich \
    ollama \
    langchain langchain-google-genai \
    deepagents \
    tavily-python \
    streamlit

# 4. Register the kernel so Jupyter sees it
python -m ipykernel install --user --name geoagent --display-name "GeoAgent (3.12)"
```

---

## Option B — pip from pyproject.toml

Use this if you prefer a plain Python virtual environment.

```bash
# 1. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install everything declared in pyproject.toml
pip install -e .

# 3. Register the kernel
pip install ipykernel
python -m ipykernel install --user --name geoagent --display-name "GeoAgent (3.12)"
```

> **Note:** On some systems `rasterio` and `geopandas` require system-level GDAL. If `pip install -e .` fails, install GDAL first (`brew install gdal` on Mac, `apt install libgdal-dev` on Linux) or switch to Option A.

---

## Launch Jupyter

```bash
conda activate geoagent          # or: source .venv/bin/activate
jupyter notebook                  # classic Notebook
# or
jupyter lab                       # JupyterLab
```

Open any notebook in `Lectures/` or `slides/` and select the **GeoAgent (3.12)** kernel.

---

## Verify the install

Run this in a notebook cell to confirm all Session 1 packages are available:

```python
# Session 1 stack
import geopandas, rasterio, rioxarray, xarray, rasterstats, affine
import folium, contextily
# Session 2 stack
import lonboard, geowombat, duckdb, dask_geopandas, pyarrow
# Base
import numpy, pandas, matplotlib

print("geopandas  :", geopandas.__version__)
print("rasterio   :", rasterio.__version__)
print("xarray     :", xarray.__version__)
print("rasterstats:", rasterstats.__version__)
print("folium     :", folium.__version__)
print("lonboard   :", lonboard.__version__)
print("geowombat  :", geowombat.__version__)
print("duckdb     :", duckdb.__version__)
print("All packages loaded successfully ✓")
```
