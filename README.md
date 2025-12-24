# Random Sampling Locations Script Tool (ArcGIS Pro)
# Overview
This mini-project was developed as part of the course Fundamentals of Programming in GIS (GEOG 567) to explore Python automation in ArcGIS Pro. The script tool automates a multi-step spatial analysis workflow to generate random tree sampling points within suitable forest areas, removing the need for repetitive manual processing.

# Purpose
The goal of this project was to understand how custom ArcGIS script tools can improve efficiency, consistency, and usability compared to manual workflows or ModelBuilder-based automation.
# Inputs
Study Area (polygon feature class)
AVI Vegetation (polygon feature class)
DEM (raster)
Roads (feature class)
Number of random points

# Method (High-Level)
Forest suitability from AVI vegetation (Species 1 Percent > 0)
Slope suitability (< 5°) derived from DEM
Road proximity (within 1000 m buffer)
All criteria are combined to create a suitability surface
Random points are generated, filtered, and trimmed to the required count

# Output
Point Feature Class Stored in Project Default Geodatabase
# Key Takeway
This project helped me understand the practical value of Python scripting in ArcGIS Pro, including tool automation, intermediate data management, schema lock handling, and user-friendly script tool design.

# Author
Anil Basnet

MGIS, University of Calgary
