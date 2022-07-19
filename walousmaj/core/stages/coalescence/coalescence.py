"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Coalescence."""
from logging import Logger

import rasterio as rio

from walousmaj.core import Stage
from walousmaj.utils import filepath
from walousmaj.utils.enums import StageOrder, StageOutputType
from walousmaj.utils.typing import Config, Maille, Output_queue


class Coalescence(Stage):
    """Regroupement des différentes mailles.

    Cette étape est en charge du regroupement des différentes mailles en un seul raster.
    """

    def __init__(self, logger: Logger):
        super().__init__(StageOrder.COALESCENCE, logger, StageOutputType.FILE)

    def execute(self, stage_config: Config) -> Output_queue:
        self.update_ongoing_mailles()
        output_queue = []

        for object_name, input_dir in zip(["ocs", "cm"], self.input_queue):
            self.logger.info(f"Coalescence de l'{object_name}")

            # Détermination du path vers le fichier des données de sortie
            output_fp = self.default_output_filepath(suffix=object_name)

            # Détermination des fichiers d'entrée
            input_fps = list(input_dir.rglob("*.tif"))

            # Détermination de la valeur du nodata
            with rio.open(input_fps[0]) as r:
                nodata = r.nodata

            # Définition de la commande gdal: gdal_merge
            # https://gdal.org/programs/gdal_merge.html
            out_filename = output_fp
            input_files = " ".join(list(map(str, input_fps)))
            a_nodata = nodata
            merge_command = (
                f"gdal_merge.py -a_nodata {a_nodata} -o {out_filename} {input_files}"
            )

            # Exécution de la commande gdal
            self.call_cmd(merge_command)

            output_queue.append(output_fp)

        self.update_done_mailles()

        return output_queue
