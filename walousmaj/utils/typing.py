"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set de Typings propre à la librairie.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import geopandas as gpd
import pandas as pd
import numpy as np


Config = Dict[str, Any]
Input_queue = List[Path]
Maille = Union[Dict[str, str], gpd.GeoSeries, pd.Series]
Output_queue = Union[List[Path], Path]
Raster_data_meta = Tuple[np.ndarray, Dict[str, Any]]
Raster_shape = Tuple[int, int, int]
