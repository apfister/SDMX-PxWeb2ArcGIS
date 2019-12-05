# SDMX-PxWeb2ArcGIS
A collection of Geoprocessing script tools that will bring data from SDMX or PxWeb into ArcGIS.

## Background
#### SDMX
The Statistical Data and Metadata eXchange ([SDMX](https://sdmx.org/)) is an international initiative that aims at standardising and modernising ("industrialising") the mechanisms and processes for the exchange of statistical data and metadata among international organisations and their member countries.

#### PxWeb
PxWeb (and the [PxWeb API](https://pxnet2.stat.fi/api1.html)) is used to publish data from stastical authorities in many countries.

## Objective
To support countries that use these systems/standards, a handful of python-based scripts were developed to join this statistical data with geographic data. The output of these scripts are File Geodatabase Feature Classes that can be published as a service and used in web applications.

## Requirements
- Statistical data in either SDMX or PxWEb formats
  - This can be CSV files or direct API links that return JSON
- Geographic data
  - Generally speaking, administrative boundaries.
- ArcGIS Pro
- Optionally, ArcGIS Online/Enterprise for publishing the resulting datasets

## Setup
- Setup your Python Environment in ArcGIS Pro
  - Clone the default python environment
  - Activate the new, cloned python environment
  - Open Anaconda command line prompt and verify you are using the cloned environment and not the default
  - Install jsonstat.py using `pip install jsonstat.py`
  - Open ArcGIS Pro
- Create a new Project in ArcGIS Pro
- Import the Toolbox for SDMX or PxWeb into your project
- Run the tool to import data from an API or from a folder of CSV files
