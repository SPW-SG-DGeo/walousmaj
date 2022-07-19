"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Vectorization.
"""
import shlex
from logging import Logger
from subprocess import check_call
from typing import Any, Dict

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder, StageOutputType


class Vectorization(Stage):
    """Vectorisation du raster.

    Cette étape vectorise le raster pour obtenir une donnée vectorisée. Aucune
    méthode de simplification n'est implémentée.
    Note: Cette étape peut être extrêmement longue pour des grosses surfaces.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(
            StageOrder.VECTORIZATION,
            logger,
            consumer=False,
            output_type=StageOutputType.FILE,
        )

    def execute(self, stage_config: Dict[str, Any]):
        self.update_ongoing_mailles()
        output_queue = []

        for object_name, input_fp in zip(["ocs", "cm"], self.input_queue):
            self.logger.info(f"Vectorisation du raster {object_name}")

            # Détermination du path vers le fichier des données de sortie
            output_fp = self.default_output_filepath(
                suffix=object_name, ext=stage_config["output_file_extension"]
            )

            # Définition de la commande gdal: gdal_polygonize
            # https://gdal.org/programs/gdal_polygonize.html
            out_file = output_fp
            raster_file = input_fp
            vectorize_command = (
                "gdal_polygonize.py "
                f"-{stage_config['connectedness']} "
                f"-f {stage_config['output_format']} "
                f"{raster_file} {out_file}"
            )

            self.logger.debug(f"Commande gdal: {vectorize_command}")

            # Exécution de la commande gdal
            check_call(shlex.split(vectorize_command))

            output_queue.append(out_file)

        self.update_done_mailles()

        return output_queue
