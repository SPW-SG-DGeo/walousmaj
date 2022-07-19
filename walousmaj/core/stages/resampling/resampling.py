"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Resampling.
"""
from logging import Logger
from typing import Any, Dict

import rasterio as rio
from rasterio.enums import Resampling as RioResampling

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder


class Resampling(Stage):
    """Ré-échantillonnage de données de sortie du modèle.

    Ré-échantillonnage, par maille, du raster pour obtenir une résolution spatiale
    spécifique.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.RESAMPLING, logger)

    def execute(self, stage_config: Dict[str, Any]):
        for maille in self.iterate_maillage():
            self.logger.info(f"Ré-échantillonnage de la maille {maille['IMAGE_NAME']}")

            # Détermination du path vers le fichier des données d'entrée
            model_output_fp = self.get_input_filepath(maille=maille)

            # Préparation des metadata pour les données de sortie
            self.logger.debug("Détermination des nouvelles metadonnées")

            # Détermination des facteurs d'agrandissement pour la resolution spatiale
            # de sortie
            ufx = stage_config.get("upscale_factor_x")
            ufy = stage_config.get("upscale_factor_y")
            upscale_factor_x = ufx if ufx else maille.PX_X_SIZE
            upscale_factor_y = ufy if ufy else maille.PX_Y_SIZE

            new_height = int(maille.IMG_HEIGHT * upscale_factor_x)
            new_width = int(maille.IMG_WIDTH * upscale_factor_y)

            self.logger.debug("Ré-échantillonnage")
            with rio.open(model_output_fp) as model_output_raster:
                data = model_output_raster.read(
                    out_shape=(1, new_height, new_width),
                    resampling=RioResampling.nearest,
                )
                meta = model_output_raster.meta

            # Adaptation de metadonnées
            old_transform = meta["transform"]
            old_height, old_width = meta["height"], meta["width"]
            new_transform = old_transform * old_transform.scale(
                (old_width / new_width),
                (old_height / new_height),
            )
            meta["transform"] = new_transform
            meta["height"], meta["width"] = new_height, new_width

            # Détermination du path vers le fichier des données de sortie
            resample_fp = self.get_output_filepath(maille=maille)

            # Écriture des données
            with rio.open(resample_fp, "w", compress="lzw", **meta) as resample_raster:
                resample_raster.write(data)

        return self.default_output_directory
