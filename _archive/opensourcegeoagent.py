"""
OpenSourceGeoAgent: Geospatial analysis agent using Ollama for open source LLM inference.

This class provides fire analysis (NASA VIIRS), forest analysis (Global Forest Watch),
and presentation generation capabilities at municipality level (GADM Level-3).

Example usage:
-------------
    from opensourcegeoagent import OpenSourceGeoAgent

    # Initialize agent
    agent = OpenSourceGeoAgent()

    # Direct method calls
    fires = agent.analyze_fires(2024)
    forest = agent.analyze_forest()

    # Natural language interface
    response = agent.chat("What municipalities had the most fires in 2023?")

    # Automated workflows
    results = agent.run_workflow("full_report")
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal, Any, Callable
import geopandas as gpd
import pandas as pd
import folium
from datetime import date
import warnings

# Import local modules
from tools import download_viirs_snpp_peru, fires_clean
from municipality_tools import (
    download_gadm_boundaries,
    download_peru_districts,
    intersect_and_collapse_municipality,
    aggregate_points_by_district,
)
from forest_tools import (
    get_peru_forest_stats,
    summarize_forest_loss_by_region,
    get_annual_loss_time_series,
    RASTERIO_AVAILABLE,
)

# Try to import Ollama
try:
    from ollama import chat as ollama_chat
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    warnings.warn(
        "ollama package not available. Chat interface will be limited. "
        "Install with: pip install ollama"
    )


@dataclass
class OpenSourceGeoAgentConfig:
    """
    Configuration for OpenSourceGeoAgent.

    Attributes
    ----------
    model : str
        Ollama model name (e.g., "llama3.1:8b", "mistral", "qwen2.5").
    temperature : float
        Sampling temperature for LLM responses.
    context_window : int
        Maximum context window size.
    country_iso3 : str
        ISO3 country code for analysis (default: "PER" for Peru).
    gadm_level : int
        Administrative level (3 = municipalities/districts).
    base_url : str
        Ollama server URL.
    think : bool
        Enable reasoning mode in Ollama (if supported by model).
    cache_dir : str
        Directory for caching downloaded data.
    """
    model: str = "llama3.1:8b"
    temperature: float = 0.7
    context_window: int = 32768
    country_iso3: str = "PER"
    gadm_level: int = 3
    base_url: str = "http://localhost:11434"
    think: bool = True
    cache_dir: str = "./data_cache"


class OpenSourceGeoAgent:
    """
    Open-source geospatial analysis agent using Ollama for LLM inference.

    Provides fire analysis (NASA VIIRS), forest analysis (Global Forest Watch),
    and presentation generation capabilities at municipality level.

    Parameters
    ----------
    config : OpenSourceGeoAgentConfig, optional
        Agent configuration. If None, uses default settings.

    Attributes
    ----------
    config : OpenSourceGeoAgentConfig
        Agent configuration including model settings.
    layers : dict[str, gpd.GeoDataFrame]
        Loaded geospatial layers.
    analysis_results : dict[str, Any]
        Cached analysis results.
    messages : list[dict]
        Conversation history for multi-turn interactions.

    Example
    -------
    >>> agent = OpenSourceGeoAgent()
    >>> fires = agent.analyze_fires(2024)
    >>> print(f"Total fires: {fires['n_fires'].sum()}")
    """

    def __init__(self, config: Optional[OpenSourceGeoAgentConfig] = None):
        self.config = config or OpenSourceGeoAgentConfig()
        self.layers: Dict[str, gpd.GeoDataFrame] = {}
        self.analysis_results: Dict[str, Any] = {}
        self.messages: List[Dict] = []
        self._tool_definitions = self._build_tool_definitions()

    def _build_tool_definitions(self) -> List[Dict]:
        """Build Ollama-compatible tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "analyze_fires",
                    "description": "Analyze NASA VIIRS fire data for Peru at municipality level",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "integer",
                                "description": "Year to analyze (2012-present)"
                            },
                            "level": {
                                "type": "string",
                                "enum": ["year", "year_month"],
                                "description": "Temporal aggregation level"
                            }
                        },
                        "required": ["year"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_forest",
                    "description": "Analyze Global Forest Watch data at municipality level",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "threshold": {
                                "type": "integer",
                                "description": "Minimum tree cover percentage (default 30)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_choropleth_map",
                    "description": "Create an interactive choropleth map",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data_type": {
                                "type": "string",
                                "enum": ["fires", "forest"],
                                "description": "Type of data to visualize"
                            },
                            "value_col": {
                                "type": "string",
                                "description": "Column to visualize"
                            }
                        },
                        "required": ["data_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_presentation",
                    "description": "Generate a Marp presentation with analysis results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string",
                                "enum": ["fires", "forest", "combined"],
                                "description": "Type of analysis to include"
                            }
                        },
                        "required": ["analysis_type"]
                    }
                }
            }
        ]

    # -------------------------------------------------------------------------
    # Core Analysis Methods
    # -------------------------------------------------------------------------

    def analyze_fires(
        self,
        year: int,
        level: Literal["year", "year_month"] = "year",
        agg_extra: Optional[Dict[str, str]] = None
    ) -> gpd.GeoDataFrame:
        """
        Analyze NASA VIIRS fire data at municipality level.

        Parameters
        ----------
        year : int
            Year to analyze (2012-present).
        level : str
            Temporal aggregation: 'year' or 'year_month'.
        agg_extra : dict, optional
            Additional aggregations like {'frp': 'sum'}.

        Returns
        -------
        gpd.GeoDataFrame
            Fire counts per municipality with columns:
            - GID_3, NAME_3: Municipality ID and name
            - NAME_2, NAME_1: Province and region names
            - year, [month]: Time keys
            - n_fires: Fire count
            - [frp]: Sum of fire radiative power (if requested)
            - geometry: Municipality polygon
        """
        if agg_extra is None:
            agg_extra = {'frp': 'sum'}

        print(f"Downloading fire data for {year}...")
        fires_df = download_viirs_snpp_peru(year)

        print("Cleaning fire data...")
        fires_gdf = fires_clean(fires_df)

        # Get municipality boundaries
        if 'boundaries_lvl3' not in self.layers:
            print("Downloading municipality boundaries (GADM Level-3)...")
            self.layers['boundaries_lvl3'] = download_peru_districts()

        print(f"Aggregating {len(fires_gdf)} fires by municipality...")
        result = intersect_and_collapse_municipality(
            points_gdf=fires_gdf,
            boundaries_gdf=self.layers['boundaries_lvl3'],
            id_col="GID_3",
            level=level,
            agg_extra=agg_extra,
            keep_attrs=["NAME_3", "NAME_2", "NAME_1"]
        )

        self.analysis_results['fires'] = result
        self.analysis_results['fires_year'] = year

        print(f"Analysis complete. {result['n_fires'].sum()} fires across {len(result)} municipalities.")
        return result

    def analyze_forest(
        self,
        year_start: int = 2000,
        year_end: int = 2024,
        threshold: int = 30,
        sample_n: Optional[int] = None
    ) -> gpd.GeoDataFrame:
        """
        Analyze Global Forest Watch data at municipality level.

        Parameters
        ----------
        year_start : int
            Start year for loss analysis.
        year_end : int
            End year for loss analysis.
        threshold : int
            Minimum tree cover % to consider as forest (default 30).
        sample_n : int, optional
            Only analyze first N municipalities (for testing).

        Returns
        -------
        gpd.GeoDataFrame
            Forest statistics per municipality:
            - GID_3, NAME_3, NAME_2, NAME_1: Admin hierarchy
            - forest_area_2000_ha: Forest area in year 2000
            - loss_total_ha: Total forest loss
            - gain_area_ha: Forest gain 2000-2012
            - net_change_ha: gain - loss
            - loss_by_year: Dict of annual loss
        """
        if not RASTERIO_AVAILABLE:
            raise ImportError(
                "rasterio is required for forest analysis. "
                "Install with: pip install rasterio"
            )

        print("Running forest analysis pipeline...")
        result = get_peru_forest_stats(
            year_range=(year_start, year_end),
            threshold=threshold,
            cache_dir=self.config.cache_dir,
            sample_n=sample_n
        )

        self.analysis_results['forest'] = result
        return result

    def aggregate_by_municipality(
        self,
        point_gdf: gpd.GeoDataFrame,
        value_cols: List[str],
        agg_funcs: Dict[str, str]
    ) -> gpd.GeoDataFrame:
        """
        Generic point-to-polygon aggregation at municipality level.

        Parameters
        ----------
        point_gdf : gpd.GeoDataFrame
            Point data to aggregate.
        value_cols : list[str]
            Columns to aggregate.
        agg_funcs : dict[str, str]
            Aggregation functions per column.

        Returns
        -------
        gpd.GeoDataFrame
            Aggregated data by municipality.
        """
        if 'boundaries_lvl3' not in self.layers:
            self.layers['boundaries_lvl3'] = download_peru_districts()

        return aggregate_points_by_district(
            points_gdf=point_gdf,
            value_cols=value_cols,
            agg_funcs=agg_funcs,
            boundaries_gdf=self.layers['boundaries_lvl3']
        )

    def download_boundaries(
        self,
        level: int = 3,
        iso3: str = None
    ) -> gpd.GeoDataFrame:
        """
        Download GADM boundaries at specified level.

        Parameters
        ----------
        level : int
            Administrative level (1=regions, 2=provinces, 3=districts).
        iso3 : str, optional
            Country ISO3 code. Uses config default if None.

        Returns
        -------
        gpd.GeoDataFrame
            Administrative boundaries.
        """
        iso3 = iso3 or self.config.country_iso3
        gdf = download_gadm_boundaries(iso3, level)
        self.layers[f'boundaries_lvl{level}'] = gdf
        return gdf

    # -------------------------------------------------------------------------
    # Output Methods
    # -------------------------------------------------------------------------

    def create_choropleth_map(
        self,
        data: gpd.GeoDataFrame = None,
        value_col: str = "n_fires",
        title: str = "Fire Count",
        output_path: str = None,
        data_type: str = None
    ) -> str:
        """
        Create interactive Folium choropleth map.

        Parameters
        ----------
        data : gpd.GeoDataFrame, optional
            Data to visualize. If None, uses cached results.
        value_col : str
            Column to visualize.
        title : str
            Legend title.
        output_path : str, optional
            Path to save HTML map.
        data_type : str, optional
            Type of data ('fires' or 'forest') to use from cache.

        Returns
        -------
        str
            Path to saved map or status message.
        """
        # Get data from cache if not provided
        if data is None:
            if data_type == "fires" and 'fires' in self.analysis_results:
                data = self.analysis_results['fires']
                if value_col == "n_fires":
                    title = "Fire Count"
            elif data_type == "forest" and 'forest' in self.analysis_results:
                data = self.analysis_results['forest']
                if value_col == "n_fires":
                    value_col = "loss_total_ha"
                    title = "Forest Loss (ha)"
            else:
                raise ValueError("No data provided and no cached results available")

        # Create map centered on Peru
        m = folium.Map(
            location=[-9.2, -75.0],
            zoom_start=5,
            tiles="cartodbpositron"
        )

        # Determine ID and name columns
        id_col = 'GID_3' if 'GID_3' in data.columns else 'GID_1'
        name_col = 'NAME_3' if 'NAME_3' in data.columns else 'NAME_1'

        # Create choropleth
        folium.Choropleth(
            geo_data=data.to_json(),
            data=data,
            columns=[id_col, value_col],
            key_on=f"feature.properties.{id_col}",
            fill_color="YlOrRd",
            fill_opacity=0.8,
            line_opacity=0.5,
            legend_name=title,
            highlight=True,
            nan_fill_color="white",
        ).add_to(m)

        # Add tooltips
        tooltip_fields = [name_col, value_col]
        tooltip_aliases = ["Municipality", title]

        if 'NAME_1' in data.columns and name_col != 'NAME_1':
            tooltip_fields.append('NAME_1')
            tooltip_aliases.append("Region")

        folium.GeoJson(
            data.to_json(),
            style_function=lambda x: {'fillOpacity': 0, 'weight': 0},
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=tooltip_aliases,
                localize=True,
            ),
        ).add_to(m)

        # Save if path provided
        if output_path:
            m.save(output_path)
            return output_path

        # Default save location
        default_path = f"./output/map_{value_col}_{date.today().isoformat()}.html"
        from pathlib import Path
        Path("./output").mkdir(exist_ok=True)
        m.save(default_path)
        return default_path

    def generate_presentation(
        self,
        analysis_type: Literal["fires", "forest", "combined"] = "combined",
        output_path: str = "./presentation"
    ) -> str:
        """
        Generate Marp presentation with analysis results.

        Parameters
        ----------
        analysis_type : str
            Type of analysis to include: 'fires', 'forest', or 'combined'.
        output_path : str
            Output directory for presentation.

        Returns
        -------
        str
            Path to generated presentation.
        """
        from presentation_generator import MarpGenerator

        generator = MarpGenerator(output_path)

        if analysis_type in ["fires", "combined"]:
            if 'fires' not in self.analysis_results:
                raise ValueError("Run analyze_fires() first")
            generator.add_fire_section(
                self.analysis_results['fires'],
                year=self.analysis_results.get('fires_year')
            )

        if analysis_type in ["forest", "combined"]:
            if 'forest' not in self.analysis_results:
                raise ValueError("Run analyze_forest() first")
            generator.add_forest_section(self.analysis_results['forest'])

        return generator.save()

    # -------------------------------------------------------------------------
    # Ollama Chat Interface
    # -------------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """
        Process natural language query using Ollama function calling.

        Parameters
        ----------
        user_message : str
            Natural language query.

        Returns
        -------
        str
            LLM response with analysis results.

        Example
        -------
        >>> response = agent.chat("What regions had the most fires in 2023?")
        >>> print(response)
        """
        if not OLLAMA_AVAILABLE:
            return self._fallback_chat(user_message)

        self.messages.append({"role": "user", "content": user_message})

        # System prompt
        system_message = {
            "role": "system",
            "content": (
                "You are a geospatial analysis assistant specialized in Peru environmental data. "
                "You can analyze fire data from NASA VIIRS and forest data from Global Forest Watch. "
                "When asked about fires or forests, use the appropriate tool to fetch and analyze data. "
                "Always provide clear summaries of the analysis results."
            )
        }

        messages = [system_message] + self.messages

        try:
            # Call Ollama with tools
            response = ollama_chat(
                model=self.config.model,
                messages=messages,
                tools=self._tool_definitions,
            )

            # Handle tool calls
            if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
                for call in response.message.tool_calls:
                    result = self._execute_tool(call)
                    self.messages.append({
                        'role': 'tool',
                        'content': result
                    })

                # Get final response after tool execution
                response = ollama_chat(
                    model=self.config.model,
                    messages=[system_message] + self.messages,
                )

            assistant_message = response.message.content
            self.messages.append({"role": "assistant", "content": assistant_message})
            return assistant_message

        except Exception as e:
            error_msg = f"Error communicating with Ollama: {e}"
            return self._fallback_chat(user_message) + f"\n\n(Note: {error_msg})"

    def _execute_tool(self, tool_call) -> str:
        """Execute a tool call and return result as string."""
        name = tool_call.function.name
        args = tool_call.function.arguments

        if name == "analyze_fires":
            result = self.analyze_fires(**args)
            return self._summarize_geodataframe(result, "fires")
        elif name == "analyze_forest":
            result = self.analyze_forest(**args)
            return self._summarize_geodataframe(result, "forest")
        elif name == "create_choropleth_map":
            path = self.create_choropleth_map(**args)
            return f"Map created and saved to: {path}"
        elif name == "generate_presentation":
            path = self.generate_presentation(**args)
            return f"Presentation generated at: {path}"
        else:
            return f"Unknown tool: {name}"

    def _fallback_chat(self, user_message: str) -> str:
        """Fallback for when Ollama is not available."""
        user_lower = user_message.lower()

        if "fire" in user_lower:
            # Try to extract year
            import re
            year_match = re.search(r'20\d{2}', user_message)
            year = int(year_match.group()) if year_match else date.today().year - 1

            try:
                result = self.analyze_fires(year)
                return self._summarize_geodataframe(result, "fires")
            except Exception as e:
                return f"Error analyzing fires: {e}"

        elif "forest" in user_lower:
            try:
                result = self.analyze_forest(sample_n=100)  # Sample for speed
                return self._summarize_geodataframe(result, "forest")
            except Exception as e:
                return f"Error analyzing forest: {e}"

        else:
            return (
                "I can help you with fire and forest analysis for Peru. "
                "Try asking about:\n"
                "- Fire data for a specific year (e.g., 'What fires occurred in 2023?')\n"
                "- Forest loss analysis (e.g., 'What is the forest loss by municipality?')\n"
                "- Creating maps or presentations"
            )

    def _summarize_geodataframe(
        self,
        gdf: gpd.GeoDataFrame,
        data_type: str,
        top_n: int = 10
    ) -> str:
        """Create text summary of GeoDataFrame for LLM context."""
        summary = f"Analysis results ({len(gdf)} municipalities):\n\n"

        if data_type == "fires" and 'n_fires' in gdf.columns:
            total = gdf['n_fires'].sum()
            summary += f"Total fire detections: {total:,}\n\n"
            summary += "Top 10 municipalities by fire count:\n"

            cols = ['NAME_3', 'NAME_1', 'n_fires']
            if 'frp' in gdf.columns:
                cols.append('frp')

            top = gdf.nlargest(top_n, 'n_fires')[cols]
            summary += top.to_string(index=False)

        elif data_type == "forest" and 'loss_total_ha' in gdf.columns:
            total_loss = gdf['loss_total_ha'].sum()
            total_gain = gdf.get('gain_area_ha', pd.Series([0])).sum()

            summary += f"Total forest loss: {total_loss:,.0f} hectares\n"
            summary += f"Total forest gain: {total_gain:,.0f} hectares\n\n"
            summary += "Top 10 municipalities by forest loss:\n"

            cols = ['NAME_3', 'NAME_1', 'loss_total_ha']
            top = gdf.nlargest(top_n, 'loss_total_ha')[cols]
            summary += top.to_string(index=False)

        return summary

    # -------------------------------------------------------------------------
    # Workflow Methods
    # -------------------------------------------------------------------------

    def run_workflow(
        self,
        workflow: Literal["fire_analysis", "forest_analysis", "full_report"]
    ) -> Dict[str, Any]:
        """
        Execute predefined analysis workflows.

        Parameters
        ----------
        workflow : str
            Workflow type:
            - 'fire_analysis': Download and analyze fire data
            - 'forest_analysis': Download and analyze forest data
            - 'full_report': Both analyses plus presentation

        Returns
        -------
        dict
            Results including GeoDataFrames, map paths, and presentation path.
        """
        results = {}
        current_year = date.today().year

        if workflow in ["fire_analysis", "full_report"]:
            print("=== Fire Analysis ===")
            results['fires'] = self.analyze_fires(current_year - 1)
            results['fire_map'] = self.create_choropleth_map(
                results['fires'],
                'n_fires',
                'Fire Count',
                f'./output/fires_{current_year-1}.html'
            )

        if workflow in ["forest_analysis", "full_report"]:
            print("\n=== Forest Analysis ===")
            results['forest'] = self.analyze_forest(sample_n=100)  # Sample for demo
            results['forest_map'] = self.create_choropleth_map(
                results['forest'],
                'loss_total_ha',
                'Forest Loss (ha)',
                './output/forest_loss.html'
            )

        if workflow == "full_report":
            print("\n=== Generating Presentation ===")
            results['presentation'] = self.generate_presentation("combined")

        return results

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from cached analysis results."""
        stats = {}

        if 'fires' in self.analysis_results:
            fires = self.analysis_results['fires']
            stats['fires'] = {
                'total_fires': int(fires['n_fires'].sum()),
                'municipalities_affected': len(fires[fires['n_fires'] > 0]),
                'year': self.analysis_results.get('fires_year'),
                'top_municipality': fires.nlargest(1, 'n_fires')[['NAME_3', 'n_fires']].to_dict('records')[0]
            }

        if 'forest' in self.analysis_results:
            forest = self.analysis_results['forest']
            stats['forest'] = {
                'total_loss_ha': float(forest['loss_total_ha'].sum()),
                'total_gain_ha': float(forest.get('gain_area_ha', pd.Series([0])).sum()),
                'municipalities_analyzed': len(forest)
            }

        return stats
