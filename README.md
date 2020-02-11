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
- Statistical data in either SDMX or PxWeb formats
  - This can be CSV files or direct API links that return JSON
- Geographic data
  - Generally speaking, administrative boundaries.
- ArcGIS Pro
- ArcGIS Online/Enterprise for publishing the resulting datasets

## Setup
- Setup your Python Environment in ArcGIS Pro
  - Clone the default python environment (documentation [here](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm#ESRI_SECTION2_61E4CFA5BAC144659038854CADEFC625))
  - [Activate](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm#ESRI_SECTION2_6D0EEF731E2248A6BB91640C7D53BEAB) the new, cloned python environment
  - Open Anaconda command line prompt and verify you are using the cloned environment and not the default
    - The command prompt can be found under **ArcGIS** in the start menu. If it is not there and, assuming you have installed ArcGIS Pro @ `c:\Program Files\ArcGIS`, the command prompt can be found at `C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\proenv.bat`
  - Install jsonstat.py by typing `pip install jsonstat.py` in the command prompt
  - Open ArcGIS Pro
- Create a new Project in ArcGIS Pro
- Import the Toolbox for SDMX or PxWeb into your project
- Run the tool to import data from an API or from a folder of CSV files

## Running the Tools
SDMX

[TODO]

PxWeb

[TODO]

