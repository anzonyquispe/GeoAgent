"""
Marp Presentation Generator for GeoAgent analysis results.

This module generates Marp-compatible Markdown presentations from
fire and forest analysis results.

Marp: https://marp.app/
Install CLI: npm install -g @marp-team/marp-cli
Export: marp presentation.md -o presentation.html
"""

from pathlib import Path
from datetime import date
from typing import Optional, List, Dict
import geopandas as gpd
import pandas as pd

# Try to import matplotlib for chart generation
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class MarpGenerator:
    """
    Generate Marp slide presentations from GeoAgent analysis results.

    Parameters
    ----------
    output_dir : str
        Output directory for presentation files.
    theme : str
        Marp theme name (default, gaia, uncover).
    title : str
        Presentation title.

    Example
    -------
    >>> generator = MarpGenerator("./presentation")
    >>> generator.add_fire_section(fires_gdf, year=2024)
    >>> generator.add_forest_section(forest_gdf)
    >>> path = generator.save()
    >>> print(f"Presentation saved to: {path}")
    """

    TEMPLATE = """---
marp: true
theme: {theme}
paginate: true
backgroundColor: #ffffff
style: |
  section {{
    font-family: 'Helvetica Neue', Arial, sans-serif;
  }}
  h1 {{
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
  }}
  h2 {{
    color: #34495e;
  }}
  table {{
    font-size: 0.8em;
    width: 100%;
  }}
  th {{
    background-color: #3498db;
    color: white;
  }}
  .columns {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }}
  .highlight {{
    background-color: #f39c12;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
  }}
  img {{
    max-width: 100%;
    height: auto;
  }}
---

# {title}
## Peru Environmental Analysis Report

**Generated:** {date}
**Data Sources:** NASA FIRMS (VIIRS), Global Forest Watch (Hansen)

![bg right:30% opacity:0.3](https://upload.wikimedia.org/wikipedia/commons/c/cf/Flag_of_Peru.svg)

---

"""

    def __init__(
        self,
        output_dir: str = "./presentation",
        theme: str = "default",
        title: str = "Peru Environmental Analysis"
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = self.output_dir / "assets"
        self.assets_dir.mkdir(exist_ok=True)
        self.theme = theme
        self.title = title
        self.content = ""
        self._add_header()

    def _add_header(self):
        """Initialize presentation with header slide."""
        self.content = self.TEMPLATE.format(
            theme=self.theme,
            title=self.title,
            date=date.today().strftime("%B %d, %Y")
        )

    def add_slide(self, content: str):
        """Add a raw slide to the presentation."""
        self.content += content + "\n\n---\n\n"

    def add_fire_section(
        self,
        fires_gdf: gpd.GeoDataFrame,
        year: Optional[int] = None,
        top_n: int = 10
    ):
        """
        Add fire analysis slides to presentation.

        Parameters
        ----------
        fires_gdf : gpd.GeoDataFrame
            Fire analysis results from OpenSourceGeoAgent.
        year : int, optional
            Year of analysis.
        top_n : int
            Number of top municipalities to show.
        """
        year = year or date.today().year - 1

        # Calculate summary stats
        total_fires = fires_gdf['n_fires'].sum() if 'n_fires' in fires_gdf.columns else 0
        total_frp = fires_gdf['frp'].sum() if 'frp' in fires_gdf.columns else 0
        affected = len(fires_gdf[fires_gdf.get('n_fires', 0) > 0])

        # Summary slide
        self.content += f"""
# Fire Analysis Results
## Year {year}

<div class="columns">
<div>

### Key Statistics

| Metric | Value |
|:-------|------:|
| **Total Fire Detections** | {total_fires:,} |
| **Fire Radiative Power** | {total_frp:,.0f} MW |
| **Municipalities Affected** | {affected:,} |
| **Analysis Level** | District (GADM-3) |

</div>
<div>

### Data Source
- **Satellite:** VIIRS SNPP
- **Resolution:** 375m active fire
- **Provider:** NASA FIRMS

</div>
</div>

---

"""

        # Top municipalities table
        cols = ['NAME_3', 'NAME_1', 'n_fires']
        if 'frp' in fires_gdf.columns:
            cols.append('frp')

        top = fires_gdf.nlargest(top_n, 'n_fires')[cols].copy()

        self.content += f"""
# Top {top_n} Municipalities by Fire Count

| Rank | District | Region | Fires | FRP (MW) |
|:----:|:---------|:-------|------:|---------:|
"""
        for idx, row in enumerate(top.itertuples(), 1):
            frp = f"{row.frp:,.0f}" if hasattr(row, 'frp') else "N/A"
            self.content += f"| {idx} | {row.NAME_3} | {row.NAME_1} | {row.n_fires:,} | {frp} |\n"

        self.content += "\n---\n\n"

        # Generate choropleth image if matplotlib available
        if MATPLOTLIB_AVAILABLE:
            fig_path = self._generate_fire_choropleth(fires_gdf, year)
            if fig_path:
                self.content += f"""
# Fire Distribution Map

![Fire distribution by municipality](assets/{fig_path.name})

---

"""

        # Regional summary
        regional = fires_gdf.groupby('NAME_1').agg({
            'n_fires': 'sum'
        }).reset_index().sort_values('n_fires', ascending=False).head(10)

        self.content += """
# Fire Count by Region

| Rank | Region | Total Fires |
|:----:|:-------|------------:|
"""
        for idx, row in enumerate(regional.itertuples(), 1):
            self.content += f"| {idx} | {row.NAME_1} | {row.n_fires:,} |\n"

        self.content += "\n---\n\n"

    def add_forest_section(
        self,
        forest_gdf: gpd.GeoDataFrame,
        top_n: int = 10
    ):
        """
        Add forest analysis slides to presentation.

        Parameters
        ----------
        forest_gdf : gpd.GeoDataFrame
            Forest analysis results from OpenSourceGeoAgent.
        top_n : int
            Number of top municipalities to show.
        """
        # Calculate summary stats
        total_loss = forest_gdf['loss_total_ha'].sum() if 'loss_total_ha' in forest_gdf.columns else 0
        total_gain = forest_gdf['gain_area_ha'].sum() if 'gain_area_ha' in forest_gdf.columns else 0
        net_change = total_gain - total_loss

        # Summary slide
        self.content += f"""
# Forest Change Analysis
## 2001-2024 Summary

<div class="columns">
<div>

### Deforestation Statistics

| Metric | Value |
|:-------|------:|
| **Total Forest Loss** | {total_loss:,.0f} ha |
| **Total Forest Gain** | {total_gain:,.0f} ha |
| **Net Change** | {net_change:,.0f} ha |
| **Analysis Level** | District (GADM-3) |

</div>
<div>

### Data Source
- **Dataset:** Hansen Global Forest Change
- **Resolution:** 30m Landsat-based
- **Provider:** University of Maryland

</div>
</div>

---

"""

        # Top municipalities by loss
        if 'loss_total_ha' in forest_gdf.columns:
            cols = ['NAME_3', 'NAME_1', 'loss_total_ha']
            top = forest_gdf.nlargest(top_n, 'loss_total_ha')[cols].copy()

            self.content += f"""
# Top {top_n} Municipalities by Forest Loss

| Rank | District | Region | Loss (ha) |
|:----:|:---------|:-------|----------:|
"""
            for idx, row in enumerate(top.itertuples(), 1):
                self.content += f"| {idx} | {row.NAME_3} | {row.NAME_1} | {row.loss_total_ha:,.0f} |\n"

            self.content += "\n---\n\n"

        # Generate time series chart if available
        if MATPLOTLIB_AVAILABLE and 'loss_by_year' in forest_gdf.columns:
            fig_path = self._generate_loss_time_series(forest_gdf)
            if fig_path:
                self.content += f"""
# Annual Forest Loss Trend

![Annual forest loss time series](assets/{fig_path.name})

---

"""

        # Regional summary
        if 'loss_total_ha' in forest_gdf.columns:
            regional = forest_gdf.groupby('NAME_1').agg({
                'loss_total_ha': 'sum'
            }).reset_index().sort_values('loss_total_ha', ascending=False).head(10)

            self.content += """
# Forest Loss by Region

| Rank | Region | Loss (ha) |
|:----:|:-------|----------:|
"""
            for idx, row in enumerate(regional.itertuples(), 1):
                self.content += f"| {idx} | {row.NAME_1} | {row.loss_total_ha:,.0f} |\n"

            self.content += "\n---\n\n"

    def _generate_fire_choropleth(
        self,
        gdf: gpd.GeoDataFrame,
        year: int
    ) -> Optional[Path]:
        """Generate choropleth map image for fires."""
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))

            # Plot municipalities
            gdf.plot(
                column='n_fires',
                ax=ax,
                legend=True,
                cmap='YlOrRd',
                legend_kwds={
                    'label': 'Fire Count',
                    'orientation': 'horizontal',
                    'shrink': 0.6
                },
                missing_kwds={'color': 'lightgrey'}
            )

            ax.set_title(f'Fire Detections by Municipality ({year})', fontsize=14)
            ax.axis('off')

            fig_path = self.assets_dir / 'choropleth_fires.png'
            fig.savefig(fig_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            return fig_path

        except Exception as e:
            print(f"Warning: Could not generate fire choropleth: {e}")
            return None

    def _generate_loss_time_series(
        self,
        gdf: gpd.GeoDataFrame
    ) -> Optional[Path]:
        """Generate time series chart for forest loss."""
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            # Aggregate loss by year
            yearly_loss = {}
            for _, row in gdf.iterrows():
                loss_dict = row.get('loss_by_year', {})
                if isinstance(loss_dict, dict):
                    for year, loss in loss_dict.items():
                        yearly_loss[year] = yearly_loss.get(year, 0) + loss

            if not yearly_loss:
                return None

            years = sorted(yearly_loss.keys())
            losses = [yearly_loss[y] for y in years]

            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(years, losses, color='#e74c3c', alpha=0.8)

            # Add trend line
            z = np.polyfit(years, losses, 1)
            p = np.poly1d(z)
            ax.plot(years, p(years), "k--", alpha=0.5, label='Trend')

            ax.set_xlabel('Year', fontsize=12)
            ax.set_ylabel('Forest Loss (hectares)', fontsize=12)
            ax.set_title('Annual Forest Loss in Peru (2001-2024)', fontsize=14)
            ax.legend()

            # Format y-axis with thousands separator
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, p: format(int(x), ','))
            )

            fig_path = self.assets_dir / 'time_series_loss.png'
            fig.savefig(fig_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            return fig_path

        except Exception as e:
            print(f"Warning: Could not generate time series chart: {e}")
            return None

    def add_methodology_slide(self):
        """Add methodology and data sources slide."""
        self.content += """
# Data Sources & Methodology

## Fire Data
- **Source:** NASA FIRMS - VIIRS SNPP
- **Resolution:** 375m active fire detections
- **Temporal:** Daily acquisitions
- **Processing:** Spatial join with GADM Level-3 boundaries

## Forest Data
- **Source:** Global Forest Watch - Hansen et al.
- **Resolution:** 30m Landsat-based
- **Metrics:** Tree cover 2000, annual loss (2001-2024), gain (2000-2012)
- **Processing:** Zonal statistics by municipality

## Administrative Boundaries
- **Source:** GADM v4.1
- **Level:** 3 (Districts/Municipalities)
- **Units:** ~1,874 districts

---

"""

    def add_conclusions_slide(
        self,
        fires_gdf: Optional[gpd.GeoDataFrame] = None,
        forest_gdf: Optional[gpd.GeoDataFrame] = None
    ):
        """Add conclusions slide with key findings."""
        self.content += """
# Key Findings

<div class="columns">
<div>

## Fire Patterns
"""
        if fires_gdf is not None and 'n_fires' in fires_gdf.columns:
            top_fire = fires_gdf.nlargest(1, 'n_fires').iloc[0]
            self.content += f"""
- Highest fire activity in **{top_fire['NAME_1']}** region
- Top district: **{top_fire['NAME_3']}**
- Total detections: **{fires_gdf['n_fires'].sum():,}**
"""
        else:
            self.content += "\n- Fire analysis not available\n"

        self.content += """
</div>
<div>

## Deforestation Trends
"""
        if forest_gdf is not None and 'loss_total_ha' in forest_gdf.columns:
            top_loss = forest_gdf.nlargest(1, 'loss_total_ha').iloc[0]
            self.content += f"""
- Greatest loss in **{top_loss['NAME_1']}** region
- Top district: **{top_loss['NAME_3']}**
- Total loss: **{forest_gdf['loss_total_ha'].sum():,.0f}** ha
"""
        else:
            self.content += "\n- Forest analysis not available\n"

        self.content += """
</div>
</div>

---

"""

    def add_footer(self):
        """Add footer slide."""
        self.content += f"""
# Thank You

Generated with **OpenSourceGeoAgent**

**Repository:** [github.com/anzonyquispe/GeoAgent](https://github.com/anzonyquispe/GeoAgent)

**Date:** {date.today().strftime("%B %d, %Y")}

---

*Analysis powered by open-source tools and open data*
"""

    def save(self, filename: str = "analysis_report.md") -> str:
        """
        Save the Marp presentation to file.

        Parameters
        ----------
        filename : str
            Output filename.

        Returns
        -------
        str
            Path to saved presentation.
        """
        # Add methodology and footer if not already added
        if "Data Sources & Methodology" not in self.content:
            self.add_methodology_slide()

        if "Thank You" not in self.content:
            self.add_footer()

        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.content)

        print(f"Presentation saved to: {output_path}")
        print(f"To export to HTML: marp {output_path} -o {output_path.with_suffix('.html')}")

        return str(output_path)

    def export_html(self, filename: str = "analysis_report.md") -> Optional[str]:
        """
        Export presentation to HTML using Marp CLI.

        Requires Marp CLI to be installed:
        npm install -g @marp-team/marp-cli

        Parameters
        ----------
        filename : str
            Source markdown filename.

        Returns
        -------
        str or None
            Path to HTML file if successful, None otherwise.
        """
        import subprocess

        md_path = self.output_dir / filename
        html_path = md_path.with_suffix('.html')

        try:
            result = subprocess.run(
                ['marp', str(md_path), '-o', str(html_path)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"HTML export successful: {html_path}")
                return str(html_path)
            else:
                print(f"Marp export failed: {result.stderr}")
                return None

        except FileNotFoundError:
            print("Marp CLI not found. Install with: npm install -g @marp-team/marp-cli")
            return None


# Import numpy for trend line calculation
try:
    import numpy as np
except ImportError:
    np = None
