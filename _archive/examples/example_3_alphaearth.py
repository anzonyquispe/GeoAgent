#!/usr/bin/env python3
"""
Example 3: Foundation Models for Spatial Analysis (AlphaEarth)
==============================================================

This example demonstrates how foundation models like Google's
AlphaEarth can generate spatial embeddings - numerical "fingerprints"
of places that capture complex patterns from satellite imagery.

Key Concepts:
- Embeddings: 64-dimensional vectors representing 10m x 10m pixels
- Clustering: Group similar areas by their embeddings
- Prediction: Use embeddings to predict attributes (land use, age, etc.)

Run time: ~5 seconds (simulated, no API required)
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict

print("=" * 60)
print("EXAMPLE 3: AlphaEarth Foundation Models")
print("=" * 60)

# ============================================================
# STEP 1: Understanding Embeddings
# ============================================================
print("\n[Step 1] Understanding Spatial Embeddings...")

print("""
What are Embeddings?
--------------------
Embeddings are numerical "fingerprints" of places. AlphaEarth
processes satellite imagery and compresses each 10m x 10m pixel
into a 64-dimensional vector that captures:

  - Land cover type (urban, forest, water, agriculture)
  - Building density and patterns
  - Vegetation health
  - Infrastructure presence
  - Temporal changes

Traditional approach:    Image -> Manual classification -> Land use map
Foundation model:        Image -> AI embedding -> Rich numerical features
""")

# Simulate embedding structure
@dataclass
class SpatialEmbedding:
    """Represents a 10m x 10m pixel embedding."""
    pixel_id: str
    lat: float
    lon: float
    embedding: np.ndarray  # 64-dimensional vector
    year: int

# ============================================================
# STEP 2: Simulate AlphaEarth Embeddings
# ============================================================
print("\n[Step 2] Simulating AlphaEarth Embeddings...")

# Simulate different land types with distinct embedding patterns
np.random.seed(42)

def generate_embedding(land_type: str) -> np.ndarray:
    """Generate simulated embedding based on land type."""
    base = np.random.randn(64) * 0.1

    if land_type == "urban":
        base[0:16] += 0.8  # Urban features in first dimensions
    elif land_type == "forest":
        base[16:32] += 0.9  # Vegetation features
    elif land_type == "agriculture":
        base[32:48] += 0.7  # Agricultural patterns
    elif land_type == "water":
        base[48:64] += 0.85  # Water signatures

    return base / np.linalg.norm(base)  # Normalize

# Generate sample pixels
land_types = ["urban", "forest", "agriculture", "water", "forest", "urban"]
sample_embeddings = []

print("\n  Sample embeddings generated:")
print(f"  {'Pixel':<10} {'Land Type':<12} {'Embedding (first 5 dims)'}")
print("  " + "-" * 50)

for i, land_type in enumerate(land_types):
    emb = SpatialEmbedding(
        pixel_id=f"PX_{i:04d}",
        lat=-12.0 + i * 0.01,
        lon=-77.0 + i * 0.01,
        embedding=generate_embedding(land_type),
        year=2024
    )
    sample_embeddings.append(emb)
    dims = ", ".join([f"{x:.2f}" for x in emb.embedding[:5]])
    print(f"  {emb.pixel_id:<10} {land_type:<12} [{dims}, ...]")

# ============================================================
# STEP 3: Clustering Similar Areas
# ============================================================
print("\n[Step 3] Clustering Similar Areas...")

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Compare all pairs
print("\n  Similarity Matrix (cosine similarity):")
print(f"  {'':>10}", end="")
for emb in sample_embeddings[:4]:
    print(f"{emb.pixel_id:>10}", end="")
print()

for i, emb_i in enumerate(sample_embeddings[:4]):
    print(f"  {emb_i.pixel_id:>10}", end="")
    for j, emb_j in enumerate(sample_embeddings[:4]):
        sim = cosine_similarity(emb_i.embedding, emb_j.embedding)
        print(f"{sim:>10.2f}", end="")
    print(f"  ({land_types[i]})")

print("""
Interpretation:
- High similarity (>0.8): Same land type
- Low similarity (<0.3): Different land types
- Embeddings cluster similar areas automatically!
""")

# ============================================================
# STEP 4: Predicting Attributes from Embeddings
# ============================================================
print("\n[Step 4] Predicting Attributes from Embeddings...")

print("""
Use Case: Predict Building Age from Embeddings
-----------------------------------------------
Instead of manual surveys, we can:
1. Get embeddings for buildings with known ages
2. Train a model on these embeddings
3. Predict ages for buildings without data
""")

# Simulate prediction
buildings = [
    {"id": "B001", "known_age": 2015, "embedding_type": "urban"},
    {"id": "B002", "known_age": 1985, "embedding_type": "urban"},
    {"id": "B003", "known_age": None, "embedding_type": "urban"},  # To predict
]

print("\n  Building Age Prediction:")
print(f"  {'Building':<10} {'Known Age':<12} {'Predicted':<12} {'Confidence'}")
print("  " + "-" * 50)

for b in buildings:
    if b["known_age"]:
        print(f"  {b['id']:<10} {b['known_age']:<12} {'(training)':<12} -")
    else:
        # Simulate prediction
        predicted_age = 1995  # Would come from model
        confidence = 0.78
        print(f"  {b['id']:<10} {'Unknown':<12} {predicted_age:<12} {confidence:.0%}")

# ============================================================
# STEP 5: Public Policy Applications
# ============================================================
print("\n" + "=" * 60)
print("PUBLIC POLICY APPLICATIONS")
print("=" * 60)

print("""
AlphaEarth embeddings enable new policy analyses:

1. URBAN PLANNING
   - Identify informal settlements by embedding patterns
   - Track urban expansion over time (2017-2024 embeddings)
   - Find similar neighborhoods for policy comparison

2. ENVIRONMENTAL MONITORING
   - Detect deforestation patterns before visible
   - Monitor agricultural encroachment on forests
   - Track ecosystem health changes

3. DISASTER RESPONSE
   - Rapidly assess damage by comparing pre/post embeddings
   - Identify vulnerable areas with similar risk profiles
   - Prioritize recovery based on infrastructure patterns

4. INFRASTRUCTURE ASSESSMENT
   - Estimate building ages without surveys
   - Identify areas needing infrastructure upgrades
   - Plan service delivery based on settlement patterns

5. EQUITY ANALYSIS
   - Compare development levels across regions
   - Identify underserved areas by embedding characteristics
   - Track policy impacts over time
""")

# ============================================================
# STEP 6: Code Example for Real Usage
# ============================================================
print("\n" + "=" * 60)
print("REAL USAGE EXAMPLE (Google Earth Engine)")
print("=" * 60)

code_example = '''
import ee

# Initialize Earth Engine
ee.Initialize()

# Access AlphaEarth embeddings
alphaearth = ee.ImageCollection("projects/google/alphaearth_foundations")

# Get embeddings for a region of interest
roi = ee.Geometry.Rectangle([-77.1, -12.1, -76.9, -11.9])  # Lima

# Filter by year and get embeddings
embeddings_2024 = alphaearth.filterDate("2024-01-01", "2024-12-31") \\
                            .filterBounds(roi) \\
                            .first()

# Sample embeddings at building locations
buildings = ee.FeatureCollection("users/myproject/lima_buildings")
sampled = embeddings_2024.sampleRegions(
    collection=buildings,
    scale=10,  # 10m resolution
    geometries=True
)

# Export for analysis
ee.batch.Export.table.toDrive(
    collection=sampled,
    description="lima_building_embeddings",
    fileFormat="Parquet"
)
'''

print(code_example)

print("=" * 60)
print("Example completed successfully!")
print("=" * 60)
