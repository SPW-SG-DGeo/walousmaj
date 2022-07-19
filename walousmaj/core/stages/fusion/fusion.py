"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Fusion.
"""
from logging import Logger
from typing import Any, Dict, List

import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio import features
from rasterio.enums import MergeAlg
from shapely.geometry import box

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder
from walousmaj.utils.typing import Raster_data_meta


class Fusion(Stage):
    """Fusion des doubles labels.

    Cette étape permet l'étagement de labels pour obtenir des doubles labels. Ainsi
    un label secondaire peut être ajouté au label prédit par le modèle (classe vue du
    ciel).
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.FUSION, logger)

    def execute(self, stage_config: Dict[str, Any]):
        sources = stage_config["sources"]
        n_sources = len(sources)
        for maille in self.iterate_maillage():
            self.logger.info(
                f"Fusion des double labels pour la maille {maille['IMAGE_NAME']}"
            )

            # Détermination du path vers le fichier des données d'entrée
            resample_fp = self.get_input_filepath(maille)

            # Extraction des données d'entrée et de ses métadonnées
            with rio.open(resample_fp) as raster:
                bbox = gpd.GeoDataFrame(crs=raster.crs, geometry=[box(*raster.bounds)])

                # Fusion des labels secondaires
                for idx, (substage_name, kwargs) in enumerate(sources.items(), start=0):
                    self.logger.debug(f"[{idx}/{n_sources}] - {substage_name}")
                    if idx == 0:
                        data = raster.read()
                        meta = raster.meta
                    data, meta = self.fuse(data, meta, bbox, **kwargs)

            # Détermination du path vers le fichier des données de sortie
            fusion_fp = self.get_output_filepath(maille=maille)

            # Sauvegarde de données fusionnées
            self.logger.debug(f"Sauvegarde des données fusionnées ({fusion_fp})")
            with rio.open(fusion_fp, "w", **meta) as fused_raster:
                fused_raster.write(data.astype("uint8"))

        return self.default_output_directory

    @staticmethod
    def fuse(
        raster_data: np.ndarray,
        raster_meta: Dict[str, Any],
        raster_bbox: gpd.GeoDataFrame,
        filter_on_labels: List[int],
        shapes_filepath: str,
        buffer: int,
        main_label: int,
    ) -> Raster_data_meta:
        """Créer des doubles labels suivant les données vectorielles externes
        `shapes_filepath`.

        :param raster_data: Données dérivées des prédictions du modèle.
        :type raster_data: np.ndarray
        :param raster_meta: Métadonnées du raster d'entrée.
        :type raster_meta: Dict[str, Any]
        :param raster_bbox: Bounding box du raster d'entrée.
        :type raster_bbox: gpd.GeoDataFrame
        :param filter_on_labels: Classes principales sur lequelles l'étagement du label
            secondaire peut s'appliquer.
        :type filter_on_labels: List[int]
        :param shapes_filepath: Données vectorielles contenant les geometries sur
            lesquelles le label secondaire doit s'appliquer.
        :type shapes_filepath: str
        :param buffer: Erosion à appliquer aux géométries de `shapes_filepath`.
        :type buffer: int
        :param main_label: Label secondaire.
        :type main_label: int
        :return: Tuple contenant les nouvelles données après fusion et les métadonnées
            associées.
        :rtype: Raster_data_meta
        """
        shapes_gdf = gpd.read_file(shapes_filepath, mask=raster_bbox)
        if len(shapes_gdf.index) == 0:
            return raster_data, raster_meta
        if buffer != 0:
            shapes_gdf = shapes_gdf.buffer(buffer)
        shapes_gdf = shapes_gdf.to_crs(raster_meta["crs"])
        mask = np.isin(raster_data, filter_on_labels)
        burned_mask = features.rasterize(
            shapes_gdf.geometry,
            out=mask.astype("uint8"),
            transform=raster_meta["transform"],
            merge_alg=MergeAlg.add,
            default_value=1,
        )
        double_label_mask = np.where(burned_mask > 1, 1, 0)

        # On multiplie les main_labels (i.e. classe secondaire/non visible du ciel) par
        # 10 pour les mettre au-dessus dans l'étagement des labels
        new_data = raster_data + (double_label_mask * main_label * 10)

        return new_data, raster_meta
