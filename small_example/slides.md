---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
style: |
  section {
    font-family: 'Helvetica Neue', Arial, sans-serif;
  }
  h1 {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
  }
  h2 {
    color: #34495e;
  }
  table {
    font-size: 0.75em;
    width: 100%;
  }
  th {
    background-color: #3498db;
    color: white;
  }
  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }
  .highlight {
    background-color: #e74c3c;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
  }
  .stat-big {
    font-size: 2.5em;
    color: #e74c3c;
    font-weight: bold;
  }
---

# Peru Fire Analysis 2024
## Municipality-Level Detection using GeoAgent

**Data Source:** NASA FIRMS (VIIRS-SNPP)
**Analysis Level:** GADM Level-3 (~1,815 districts)
**Generated:** February 2026

---

# Key Statistics

<div class="columns">
<div>

## Fire Detections

<p class="stat-big">99,932</p>

Total fire detections in Peru (2024)

</div>
<div>

## Geographic Coverage

<p class="stat-big">1,499</p>

Municipalities affected (82.5% of all districts)

</div>
</div>

---

# Top 10 Districts by Fire Count

| Rank | District | Region | Fires | FRP (MW) |
|:----:|:---------|:-------|------:|---------:|
| 1 | Nueva Requena | Ucayali | 3,763 | 47,229 |
| 2 | Callaria | Ucayali | 2,282 | 20,925 |
| 3 | Iberia | Madre de Dios | 2,159 | 25,745 |
| 4 | Irazola | Ucayali | 1,907 | 23,639 |
| 5 | Campo Verde | Ucayali | 1,760 | 16,404 |
| 6 | Masisea | Ucayali | 1,752 | 19,536 |
| 7 | Raymondi | Ucayali | 1,727 | 17,701 |
| 8 | Inapari | Madre de Dios | 1,660 | 15,539 |
| 9 | Tahuamanu | Madre de Dios | 1,507 | 15,134 |
| 10 | Puerto Bermudez | Pasco | 1,498 | 13,875 |

---

# Fire Count by Region

| Region | Fires | % of Total |
|:-------|------:|:-----------|
| Ucayali | 18,532 | 18.5% |
| San Martin | 12,842 | 12.9% |
| Loreto | 11,764 | 11.8% |
| Madre de Dios | 9,592 | 9.6% |
| Huanuco | 9,581 | 9.6% |
| Junin | 5,909 | 5.9% |
| Cajamarca | 4,677 | 4.7% |
| Cusco | 3,459 | 3.5% |
| La Libertad | 2,885 | 2.9% |
| Amazonas | 2,862 | 2.9% |

---

# Key Findings

## Amazon Region Dominance
- **Top 5 regions** account for **62%** of all fires
- Ucayali alone has **18.5%** of national fires
- Clear concentration in Amazon basin

## Fire Radiative Power
- Highest FRP in Nueva Requena: **47,229 MW**
- Indicates intense, large-scale burning
- Agricultural expansion & deforestation patterns

---

# Methodology

## Data Pipeline

1. **Download** VIIRS-SNPP data from NASA FIRMS API
2. **Clean** and convert to GeoDataFrame (EPSG:4326)
3. **Load** GADM Level-3 boundaries (1,815 districts)
4. **Spatial Join** fire points within district polygons
5. **Aggregate** counts and FRP by municipality

## Tools Used
- **GeoPandas** - Spatial operations
- **Folium** - Interactive maps
- **OpenSourceGeoAgent** - Analysis orchestration

---

# Interactive Map

The choropleth map shows fire count by municipality:

- **Dark red** = High fire activity
- **Yellow** = Low fire activity
- **White** = No fires detected

**View the interactive map:**
`peru_fires_2024_municipalities.html`

---

# Administrative Levels

| Level | Name | Count | This Analysis |
|:------|:-----|------:|:--------------|
| 1 | Regions | 26 | Aggregation |
| 2 | Provinces | ~196 | - |
| **3** | **Districts** | **1,815** | **Primary unit** |

Using Level-3 provides **70x more granularity** than regional analysis!

---

# Data Sources

| Dataset | Provider | Resolution |
|:--------|:---------|:-----------|
| VIIRS SNPP Active Fire | NASA FIRMS | 375m |
| Administrative Boundaries | GADM v4.1 | Vector |

## VIIRS Fire Product
- 375m spatial resolution
- Day and night detection
- Global coverage since 2012
- Fire Radiative Power (FRP) in MW

---

# OpenSourceGeoAgent

```python
from opensourcegeoagent import OpenSourceGeoAgent

# Initialize agent
agent = OpenSourceGeoAgent()

# Run fire analysis
fires = agent.analyze_fires(2024)

# Create map
agent.create_choropleth_map(
    fires, 'n_fires', 'Fire Count'
)

# Natural language query
agent.chat("What districts had the most fires?")
```

---

# Future Work

## Forest Analysis Integration
- Global Forest Watch (Hansen) data
- Tree cover loss 2001-2024
- Fire-deforestation correlation

## Temporal Analysis
- Monthly fire patterns
- Year-over-year trends
- Seasonal hotspots

## Expanded Coverage
- Other Andean countries
- Cross-border fire tracking

---

# Thank You

**Repository:** [github.com/anzonyquispe/GeoAgent](https://github.com/anzonyquispe/GeoAgent)

**Analysis Date:** February 2026
**Data Year:** 2024

---

*Analysis powered by open-source tools and open data*

*NASA FIRMS | GADM | GeoPandas | Folium*
