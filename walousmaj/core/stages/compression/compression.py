"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Compression.
"""
from logging import Logger


from walousmaj.core import Stage
from walousmaj.utils.enums import StageOrder, StageOutputType
from walousmaj.utils.typing import Config, Output_queue


class Compression(Stage):
    """Compression d'un raster.

    Cette étape se charge de la compression du raster pour que celui-ci prenne moins de
    place de stockage.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(
            StageOrder.COMPRESSION, logger, output_type=StageOutputType.FILE
        )

    def execute(self, stage_config: Config) -> Output_queue:
        self.update_ongoing_mailles()
        output_queue = []

        for object_name, input_fp in zip(["ocs", "cm"], self.input_queue):
            self.logger.info(f"Compression du raster {object_name}")

            # Détermination du path vers le fichier des données de sortie
            output_fp = self.default_output_filepath(suffix=object_name)

            # Définition de la commande gdal: gdal_translate
            # https://gdal.org/programs/gdal_translate.html
            src_dataset = input_fp
            dst_dataset = output_fp
            translate_command = (
                "gdal_translate "
                f"-co 'COMPRESS={stage_config['method'].value}' "
                f"{src_dataset} {dst_dataset}"
            )

            # Exécution de la commande gdal
            self.call_cmd(translate_command)

            output_queue.append(output_fp)

        self.update_done_mailles()

        return output_queue
