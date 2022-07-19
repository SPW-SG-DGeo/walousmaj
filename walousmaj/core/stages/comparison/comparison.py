"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Comparison.
"""
from logging import Logger

import geopandas as gpd
import numpy as np
import numpy.ma as ma
import pandas as pd
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.features import geometry_window

from walousmaj.core import Stage
from walousmaj.utils.enums import ComparisonOutputFormatEnum, StageOrder
from walousmaj.utils.mappings import ocs_double_to_main_labels_divmod as double2main
from walousmaj.utils.typing import Config, Output_queue, Raster_shape


class Comparison(Stage):
    """Comparaison de la nouvelle carte d'occupation du sol avec l'ancienne.

    Cette étape compare la carte d'occupation du sol générée par la solution avec une
    autre, typiquement plus ancienne, version de cette carte d'occupation du sol.
    Plusieurs formats pour la donnée de sortie sont supportés:
        - BINARY_MASK: Un masque booléen avec les pixels changés en True.
        - BEFORE_AFTER_2B: Un raster 2 bandes. La première bande reprend le label
            de l'ancienne version, et la deuxième bande, le label de la nouvelle
            version.
        - BEFORE_AFTER_SINGLE: Un raster 1 bande où pour les pixels changés la
            valeur est (label ancienne version * 1000) + label nouvelle version.
    """

    def __init__(self, logger: Logger):
        # Cette étape n'est pas un "consumer" car il ajoute une nouvelle donnée.
        super().__init__(StageOrder.COMPARISON, logger, consumer=False)

    def execute(self, stage_config: Config) -> Output_queue:
        self.logger.debug("Lecture de l'ancien OCS")
        with rio.open(stage_config["previous_ocs_filepath"]) as old_ocs:
            for maille in self.iterate_maillage():
                self.logger.info(f"Comparaison de la maille {maille['IMAGE_NAME']}")
                # Détermination du path vers le fichier des données d'entrée
                input_fp = self.get_input_filepath(maille)

                # Extraction des données d'entrée et de ses métadonnées
                with rio.open(input_fp) as new_ocs:
                    meta = new_ocs.meta
                    new_ocs_data = ma.masked_equal(new_ocs.read(), new_ocs.nodata)

                self.logger.debug("Extraction de la maille pour l'ancien OCS")
                old_ocs_data = self.get_ocs(old_ocs, maille, new_ocs_data.shape)

                if stage_config["only_main_label"]:
                    new_ocs_data = double2main(new_ocs_data)
                    old_ocs_data = double2main(old_ocs_data)

                # Comparison entre les deux cartes d'occupation du sol
                self.logger.debug("Comparaison")
                output_format = stage_config["output_format"]
                comparison = self.compare(old_ocs_data, new_ocs_data, output_format)

                # Preparation des metadata pour les données de sortie
                meta["dtype"] = comparison.dtype
                meta["count"] = comparison.shape[0]
                meta["nodata"] = comparison.fill_value
                kwargs = {}
                if output_format == ComparisonOutputFormatEnum.BINARY_MASK:
                    kwargs["nbits"] = 2

                # Détermination du path vers le fichier des données de sortie
                output_fp = self.get_output_filepath(maille=maille)

                # Sauvegarde de données de comparison
                self.logger.debug(f"Sauvegarde des données comparées ({output_fp})")
                with rio.open(output_fp, "w", **kwargs, **meta) as out_raster:
                    out_raster.write(comparison.filled())

        return self.default_output_directory

    @staticmethod
    def get_ocs(
        ocs: rio.DatasetReader,
        maille: pd.Series,
        out_shape: Raster_shape = (1, 2000, 2000),
        resampling: Resampling = Resampling.nearest,
    ) -> ma.MaskedArray:
        """Lit et convertit en MaskedArray (NoData masqué) un raster.

        :param ocs: Raster-Carte d'occupation du sol.
        :type ocs: rio.DatasetReader
        :param maille: La maille pour laquelle la lecture du raster doit se faire.
        :type maille: pd.Series
        :param out_shape: Les dimensions de la donnée de sortie. Par défaut, celle-ci
            est fixée à (1, 2000, 2000) puisqu'une maille fait 2km² et que la résolution
            spatiale de la carte d'occupation du sol est de 1m/pixel.
        :type out_shape: Raster_shape, optional
        :param resampling: Méthode de rééchantillonnage à utiliser si la donnée n'a pas
            nativement les dimensions prédéfinies par `out_shape`. Par défaut:
            Resampling.nearest
        :type resampling: Resampling, optional
        :return: Un MaskedArray représentant la carte d'occupation du sol pour la
            maille.
        :rtype: ma.MaskedArray
        """
        maille_geom = gpd.GeoDataFrame(geometry=[maille.geometry], crs=maille.EPSG)
        ocs_window = geometry_window(ocs, [maille_geom.to_crs(ocs.crs).geometry])
        ocs_data = ocs.read(
            window=ocs_window, out_shape=out_shape, resampling=resampling
        )
        return ma.masked_equal(ocs_data, ocs.nodata)

    @staticmethod
    def compare(
        array_1: ma.MaskedArray,
        array_2: ma.MaskedArray,
        output_format: ComparisonOutputFormatEnum,
    ) -> ma.MaskedArray:
        """Compare deux arrays suivant une méthode définie par `output_format`.

        Ces arrays doivent être des MaskedArrays où les éléments cachés sont des NoData.

        :param array_1: Premier MaskedArray de la comparaison.
        :type array_1: ma.MaskedArray
        :param array_2: Second MaskedArray de la comparaison.
        :type array_2: ma.MaskedArray
        :param output_format: Format de la donnée de sortie. Plusieurs possibilités:
            - BINARY_MASK: Un masque booléen avec les pixels changés en True.
            - BEFORE_AFTER_2B: Un raster 2 bandes. La première bande reprend le label
                de l'`array_1` et la deuxième celui de l'`array_2` pour chaque pixel
                changé. Les pixels non changés ont une valeur de 0.
            - BEFORE_AFTER_SINGLE: Un raster 1 bande où pour les pixels changés la
                valeur est (label `array_1` * 1000) + label `array_2`. Les pixels non
                changés ont une valeur de 0.
        :type output_format: ComparisonOutputFormatEnum
        :raises NotImplementedError: Cette erreur est soulevée si la valeur de
            `output_format` n'est pas connue/implémentée.
        :return: Un MaskedArray dans le format `output_format` où les éléments masqués
            correspondent à du NoData.
        :rtype: ma.MaskedArray
        """
        change_mask = np.not_equal(array_1, array_2)
        if output_format == ComparisonOutputFormatEnum.BINARY_MASK:
            return ma.MaskedArray(
                change_mask.data,
                mask=change_mask.mask,
                fill_value=2,  # nodata: Pour réduire la taille du fichier à nbits=2
                dtype="uint8",
            )
        elif output_format == ComparisonOutputFormatEnum.BEFORE_AFTER_2B:
            cm_broadcasted = np.broadcast_to(change_mask, (2, *change_mask.shape[-2:]))
            nodata_mask = np.broadcast_to(change_mask.mask, cm_broadcasted.shape)
            array_1_2 = np.concatenate([array_1, array_2])
            return ma.MaskedArray(
                np.where(cm_broadcasted, array_1_2, 0),
                mask=nodata_mask,
                fill_value=255,  # nodata
                dtype="uint8",
            )
        elif output_format == ComparisonOutputFormatEnum.BEFORE_AFTER_SINGLE:
            data = (array_1.astype("uint32") * 1000) + array_2
            return ma.MaskedArray(
                np.where(change_mask, data, 0),
                mask=change_mask.mask,
                fill_value=255,
                dtype="uint32",
            )
        else:
            raise NotImplementedError(
                "La valeur de l'argument `output_format` du `Stage` Comparison est "
                f"inconnue. Reçu: {output_format}"
            )
