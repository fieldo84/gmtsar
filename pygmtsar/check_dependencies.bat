@echo off
setlocal enabledelayedexpansion

set "packages=xarray numpy numba pandas geopandas distributed dask dask_image joblib tqdm sentineleof scipy shapely scikit-learn xmltodict rioxarray ipywidgets h5netcdf h5py nc-time-axis statsmodels pygmt vtk"

for %%p in (%packages%) do (
    echo Checking package: %%p
    conda list | findstr /C:"%%p"
    echo.
)
