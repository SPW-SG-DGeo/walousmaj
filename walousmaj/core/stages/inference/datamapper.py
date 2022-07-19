"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Mappings pour les "dataset_dicts" adaptés au format raster.
"""
import copy
from typing import Any, Dict

import numpy as np
import rasterio as rio
import torch
from detectron2.data import DatasetMapper
from rasterio import windows


__all__ = ["GeoDatasetMapper"]


class GeoDatasetMapper(DatasetMapper):
    """Un `callable` prenant un `dataset_dict` au format Detectron2 Dataset et le
    convertit au format reconnu par le modèle."""

    def get_raster(
        self,
        fp: str,
        window: windows.Window,
        channels_last: bool = True,
        dtype: str = "float32",
        boundless: bool = False,
    ):
        with rio.open(fp) as raster:
            data = raster.read(window=window, boundless=boundless, fill_value=0)
            if channels_last:
                data = np.transpose(data, (1, 2, 0))
            data = data.astype(dtype)  # shape = B x H x W

            # Extraction du nodata masque. Puisque l'étape de Preprocessing assigne le
            # même masque pour toutes les bandes, on peut se limiter à une seule.
            nodata_mask = raster.read_masks(1, window=window).squeeze()  # shape = H x W
            return (data, nodata_mask)

    def __call__(
        self,
        dataset_dict: Dict[str, Any],
        window: windows.Window,
        **kwargs,
    ) -> Dict[str, Any]:
        """Convertir le `dataset_dict` Detectron2 au format reconnu par le modèle.

        Extrait les données d'entrée et les convertit au format accepté par le modèle.

        :param dataset_dict: `dataset_dict` au format Detectron2 Dataset.
        :type dataset_dict: Dict[str, Any]
        :param window: Fenêtre/sous-region du raster à lire.
        :type window: windows.Window
        :return: `dataset_dict` au format reconnu par la modèle.
        :rtype: Dict[str, Any]
        """
        dataset_dict = copy.deepcopy(dataset_dict)
        dataset_dict["window"] = window
        input_data, input_nodata_mask = self.get_raster(
            fp=dataset_dict["file_name"], window=window, channels_last=False
        )
        dataset_dict["image"] = torch.as_tensor(
            np.ascontiguousarray(input_data.astype("long"))
        )
        dataset_dict["nodata"] = input_nodata_mask
        for key, value in kwargs.items():
            dataset_dict[key] = value
        return dataset_dict
