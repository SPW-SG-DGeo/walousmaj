"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Reprojection.
"""
import shlex
from logging import Logger
from subprocess import check_call
from typing import Any, Dict

import rasterio as rio
from pyproj import CRS

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder, StageOutputType


class Reprojection(Stage):
    """Reprojection du raster dans un nouveau système de coordonnées de référence.

    Cette étape se charge de reprojeter le raster dans le CRS défini dans la
    configuration, si nécessaire.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(
            StageOrder.REPROJECTION, logger, output_type=StageOutputType.FILE
        )

    def execute(self, stage_config: Dict[str, Any]):
        self.update_ongoing_mailles()
        output_queue = []

        for object_name, input_fp in zip(["ocs", "cm"], self.input_queue):
            self.logger.info(f"Reprojection du raster {object_name}")

            # Détermination du path vers le fichier des données de sortie
            output_fp = self.default_output_filepath(suffix=object_name)

            with rio.open(input_fp) as r:
                src_crs = r.crs
                self.logger.debug(f"CRS d'origine: {src_crs}")

            if (
                stage_config["to_srs"]
                and CRS.from_user_input(stage_config["to_srs"]) == src_crs
            ):
                # Si le CRS du raster est déjà celui souhaité, pas de reprojection
                self.logger.info(
                    "Annulation de la reprojection du raster: CRS de la source est identique au CRS souhaité."
                )
                output_queue.append(input_fp)
            else:
                # Définition de la commande gdal: gdalwarp
                # https://gdal.org/programs/gdalwarp.html
                src_dataset = input_fp
                dst_dataset = output_fp
                sc_t_srs = str(stage_config["to_srs"])
                t_srs = f"-t_srs '{sc_t_srs}' " if sc_t_srs else ""
                sc_ct = stage_config["coordinate_transform"]
                ct = f"-ct '{sc_ct}' " if sc_ct else ""
                sc_te = stage_config["target_extents"]
                te = f"-te {sc_te} " if sc_te else ""
                sc_tr = stage_config["target_resolution"]
                tr = f"-tr {sc_tr} " if sc_tr else ""
                tap = ""
                if stage_config["target_aligned_pixels"]:
                    if not tr:
                        self.logger.debug(
                            "Omission de l'option `-tap` car l'option `-tr` n'est pas fournie"
                        )
                    else:
                        tap = "-tap "
                warp_command = (
                    "gdalwarp "
                    "-r near "  # Algorithme de rééchantillonnage: Nearest neighbor
                    f"{t_srs}"  # CRS du raster de sortie
                    f"{ct}"  # Etapes de transformation
                    f"{te}"  # Extensions du raster de sortie
                    f"{tr}"  # Résolutions x et y du raster de sortie
                    f"{tap}"  # Alignement des pixels aux extensions et resolution
                    f"{src_dataset} {dst_dataset}"
                )

                self.logger.debug(f"Commande gdal: {warp_command}")

                # Exécution de la commande gdal
                check_call(shlex.split(warp_command))

                output_queue.append(output_fp)

        self.update_done_mailles()

        return output_queue
