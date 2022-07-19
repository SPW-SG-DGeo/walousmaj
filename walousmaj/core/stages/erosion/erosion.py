"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Erosion.
"""
from logging import Logger
from typing import Any, Dict

import numpy as np
import rasterio as rio
from rasterio.features import sieve

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder, StageOutputType


class Erosion(Stage):
    """Erosion des petites zones pour tenir compte de l'unité minimale de cartographie.

    Cette étape remplace les petites zones de pixels avec le même label ne satisfaisant
    pas l'unité minimale de cartographie. Pour ces zones, le label est remplacé par
    celui de la zone adjacente la plus grande.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.EROSION, logger, output_type=StageOutputType.FILE)

    def execute(self, stage_config: Dict[str, Any]):
        for maille in self.iterate_maillage():
            self.logger.info(f"Erosion de la maille {maille['IMAGE_NAME']}")

            # Détermination du path vers le fichier des données d'entrée
            input_fp = self.get_input_filepath(maille=maille)

            # Extraction des données d'entrée et de ses métadonnées
            with rio.open(input_fp) as input_raster:
                data = sieve(
                    input_raster.read(1),
                    size=stage_config["threshold"],
                    connectivity=stage_config["connectedness"],
                )
                meta = input_raster.meta

            # Détermination du path vers le fichier des données de sortie
            erosion_fp = self.get_output_filepath(maille=maille)

            # Sauvegarde des données érodées
            with rio.open(erosion_fp, "w", compress="lzw", **meta) as erosion_raster:
                erosion_raster.write(np.expand_dims(data, axis=0))

        return self.default_output_directory
