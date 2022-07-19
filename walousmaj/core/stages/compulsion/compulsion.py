"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Compulsion.
"""
from logging import Logger
from typing import Any, Dict

import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio import features
from rasterio.enums import MergeAlg
from shapely.geometry import box

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder
from walousmaj.utils.typing import Raster_data_meta


class Compulsion(Stage):
    """Forçage de données sur le raster.

    Cette étape se charge de forcer des données vectorisées directement sur les
    prédictions du modèle. Ces données remplacent donc les prédictions du modèle sans
    aucune vérification.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.COMPULSION, logger)

    def execute(self, stage_config: Dict[str, Any]):
        for maille in self.iterate_maillage():
            self.logger.info(
                "Forçage de données de correction pour "
                f"la maille {maille['IMAGE_NAME']}"
            )

            # Détermination du path vers le fichier des données d'entrée
            fusion_fp = self.get_input_filepath(maille)

            # Extraction des données d'entrée et de ses métadonnées
            with rio.open(fusion_fp) as raster:
                bbox = gpd.GeoDataFrame(crs=raster.crs, geometry=[box(*raster.bounds)])
                data = raster.read()
                meta = raster.meta
                data, meta = self.compel(data, meta, bbox, **stage_config)

            # Détermination du path vers le fichier des données de sortie
            compel_fp = self.get_output_filepath(maille=maille)

            # Sauvegarde des données après forçage
            self.logger.debug(f"Sauvegarde des données forcées ({compel_fp})")
            with rio.open(compel_fp, "w", **meta) as compelled_raster:
                compelled_raster.write(data.astype("uint8"))

        return self.default_output_directory

    def compel(
        self,
        raster_data: np.ndarray,
        raster_meta: Dict[str, Any],
        raster_bbox: gpd.GeoDataFrame,
        shapes_filepath: str,
        default_label: int = None,
    ) -> Raster_data_meta:
        """Remplacer les prédictions du modèle `raster_data` par les données
        vectorielles externes `shapes_filepath`.

        :param raster_data: Prédictions du modèle.
        :type raster_data: np.ndarray
        :param raster_meta: Métadonnées des prédictions du modèle.
        :type raster_meta: Dict[str, Any]
        :param raster_bbox: Bounding box des prédictions.
        :type raster_bbox: gpd.GeoDataFrame
        :param shapes_filepath: Données vectorielles.
        :type shapes_filepath: str
        :param default_label: Label par défaut pour le forçage des données. Par défaut,
            le label est inféré de l'attribut `value` de chaque geometry du
            `shapes_filepath`.
        :type default_label: int, optional
        :return: Tuple contenant les nouvelles données après forçage et les métadonnées
            associées.
        :rtype: Raster_data_meta
        """
        shapes_gdf = gpd.read_file(shapes_filepath, mask=raster_bbox)
        if len(shapes_gdf.index) == 0:
            self.logger.warning(f"Pas de geometries trouvées dans {shapes_filepath}")
            return raster_data, raster_meta
        shapes_gdf = shapes_gdf.to_crs(raster_meta["crs"])

        if default_label:
            shapes = shapes_gdf.geometry
        else:
            default_label = 0  # None n'est pas accepté par rasterize()
            shapes = zip(shapes_gdf.geometry, shapes_gdf.value)

        new_data = features.rasterize(
            shapes,
            out=raster_data,
            transform=raster_meta["transform"],
            merge_alg=MergeAlg.replace,
            default_value=default_label,
        )

        return new_data, raster_meta
