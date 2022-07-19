"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Cropping.
"""
from logging import Logger
from typing import Any, Dict

import geopandas as gpd
import rasterio as rio
from shapely.geometry import box

from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder, StageOutputType


class Cropping(Stage):
    """Rognage du raster selon une AOI.

    Cette étape rogne le raster selon la région d'intérêt de l'utilisateur ou selon le
    territoire wallon (par défaut).
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.CROPPING, logger, output_type=StageOutputType.FILE)

    def execute(self, stage_config: Dict[str, Any]):
        self.update_ongoing_mailles()
        output_queue = []

        for object_name, input_fp in zip(["ocs", "cm"], self.input_queue):
            self.logger.info(f"Rognage du raster {object_name}")

            # Chargement de l'AOI
            self.logger.debug(
                "Chargement de l'AOI provenant du fichier: "
                f"{stage_config['aoi_filepath']}"
            )
            aoi = gpd.read_file(stage_config["aoi_filepath"])

            # Création du masque de rognage et inversion de celui-ci
            with rio.open(input_fp) as r:
                nodata = r.nodata
                crs = r.crs
                bbox = box(*r.bounds)
            mask_filepath = self.default_output_filepath(suffix="mask", ext=".shp")
            raster_bounds = gpd.GeoDataFrame(geometry=[bbox], crs=crs)
            mask = gpd.overlay(raster_bounds.to_crs(aoi.crs), aoi, how="difference")
            if not mask.empty:
                # Sauvegarde du masque dans un fichier pour GDAL.
                # Note: un NamedTemporaryFile ne fonctionne pas pour sauver un .shp
                # car plusieurs fichiers doivent être créés.
                mask.to_file(mask_filepath)

                # Définition de la commande gdal: gdal_rasterize
                # https://gdal.org/programs/gdal_rasterize.html
                # Note: `inversion` option ne semble pas fonctionner
                dst_filename = input_fp  # Écrasement des données
                src_datasource = mask_filepath
                rasterize_command = (
                    "gdal_rasterize "
                    f"{'-at ' if stage_config['all_touched'] else ''}"
                    f"-burn {nodata} "
                    f"{src_datasource} {dst_filename}"
                )

                # Exécution de la commande gdal
                self.call_cmd(rasterize_command)
            else:
                # Si le raster est entièrement compris dans l'AOI pas besoin de rogner
                self.logger.info("Annulation du rognage du raster: inclus dans l'AOI.")

            output_fp = input_fp  # Écrasement des données

            output_queue.append(output_fp)

        self.update_done_mailles()

        return output_queue
