# Assignment 2: Identifying Rice Areas

> **Deadline: Tuesday, July 22, 2026 — end of day, Lima, Peru time (UTC−5).**

## Context

We will work with **AlphaEarth embeddings** for Bellavista, San Martín, Peru (2019). The goal is to extend the first analysis from the tutorial available [here](https://github.com/anzonyquispe/GeoAgent/blob/main/Lectures/Tutorial4_sanmartin) to generate an unsupervised classification and identify rice-growing areas using the **GloRice-I** global rice distribution dataset, available [here](https://figshare.com/articles/dataset/GloRice_I_Gridded_5-arcmin_paddy_rice_annual_distribution_maps_for_the_years_1961_to_2021/27965832/2). You may use [this Google Earth Engine tutorial](https://developers.google.com/earth-engine/tutorials/community/satellite-embedding-02-unsupervised-classification) as additional guidance.

## Tasks

### 1. Replicate the unsupervised classification

Generate an unsupervised classification following the main tutorial available [here](https://github.com/anzonyquispe/GeoAgent/blob/main/Lectures/Tutorial4_sanmartin), **excluding the slope filter**. Restrict the analysis to **cropland areas** only.

Use **Clustergram** to determine the optimal number of clusters.

Then, overlay the resulting clusters with the **GloRice-I** dataset. For **each cluster**, calculate:

* the total area covered by the cluster,
* the area within the cluster classified as rice according to the GloRice-I dataset, and
* the proportion of the cluster that corresponds to rice.

Finally, assign a cluster as **"rice"** if rice is the **majority land cover within that cluster** (i.e., rice occupies a larger area than all other land-cover types combined within the cluster). Label the remaining clusters as **non-rice**.

### 2. Compare fire occurrence between rice and non-rice areas

Using the rice and non-rice clusters identified in the previous step, quantify fire occurrence between **2017 and 2019**.

Using a fire dataset (e.g., MODIS or VIIRS active fire detections), calculate the **annual number of fire detections normalized by area** occurring within:

* the clusters classified as **rice**, and
* the clusters classified as **non-rice**.

Create a **time series line plot** with:

* the **x-axis** representing the years (2017–2019),
* the **y-axis** representing the number of fire detections, and
* **two colored lines**, one for **rice areas** and one for **non-rice areas**.

Based on the seasonal use of fire in rice cultivation, we expect the **rice areas to exhibit a higher number of fire detections than the non-rice areas** over the study period. Briefly discuss whether your results support this expectation.

## Deliverables

* One reproducible Jupyter Notebook or JavaScript script in [this folder](https://github.com/anzonyquispe/GeoAgent/tree/main/Assignments/Assignment2) showing all steps of the analysis.

**Work in groups of 2 or 3.**

**Submit by Tuesday, July 22, 2026, end of day (Lima, Peru time, UTC−5).**
