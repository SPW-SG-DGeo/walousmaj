"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Preprocessing.

ORTHO: Orthophoto 16-bits 4 bandes (rouge, vert, bleu, et infra-rouge)
MNT: Modèle numérique de terrain
MNS: Modèle numérique de surface
MNH: Modèle numérique de hauteur (MNS - MNT)
"""
from copy import deepcopy
from logging import Logger
from typing import Any, Dict, Tuple

import geopandas as gpd
import numpy as np
import numpy.ma as ma
import pandas as pd
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.features import geometry_window

from walousmaj.core import Stage
from walousmaj.utils import filepath
from walousmaj.utils.enums import StageOrder
from walousmaj.utils.typing import Raster_data_meta


class Preprocessing(Stage):
    """Pré-traitement des données et transformation en données d'entrée du modèle.

    Cette étape prépare et formate les données Ortho, MNS, et MNT pour l'étape
    Inference. Ces différentes données sont rassemblées en un raster 5 bandes (rouge,
    vert, bleu, infra-rouge, et MNH) découpé par maille.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.PREPROCESSING, logger)

    def execute(self, stage_config: Dict[str, Any]):
        ortho_dir = stage_config["ortho_directory"]
        mnt_fp, mns_fp = stage_config["mnt_filepath"], stage_config["mns_filepath"]
        self.logger.debug(f"Lecture du MNT ({mnt_fp}) et MNS ({mns_fp})")
        with rio.open(mnt_fp) as mnt, rio.open(mns_fp) as mns:
            for maille in self.iterate_maillage():
                self.logger.info(f"Pre-traitement de la maille {maille['IMAGE_NAME']}")

                # Lecture de l'orthophoto et calcul du MNH
                ortho_data, ortho_meta = self.get_ortho(ortho_dir, maille)
                mnh_data = self.get_mnh(mnt, mns, maille)

                # Concatenation et conversion en float32 pour uniformisation
                # data.shape = 5 x maille.IMG_HEIGHT x maille.IMG_WIDTH
                data = ma.concatenate(
                    [ortho_data.astype("float32"), mnh_data.astype("float32")], axis=0
                )

                # Adaptation des métadonnées
                meta = deepcopy(ortho_meta)
                meta["count"] += 1
                meta["dtype"] = "float32"

                # Création du masque représentant les pixels sans donnée
                # Rasterio: True=Pixel valide, False=Nodata
                # NumPy MaskedArray: True=Nodata, False=Pixel valide
                if ma.is_masked(data):
                    nodata_mask = ~np.any(data.mask, axis=0)
                else:
                    nodata_mask = True
                data.fill_value = meta["nodata"]

                # Détermination du path vers le fichier des données de sortie
                save_fp = self.get_output_filepath(maille=maille)

                # Sauvegarde des données d'entrée du modèle
                with rio.open(save_fp, "w", **meta) as input_raster:
                    input_raster.write(data.filled())
                    input_raster.write_mask(nodata_mask)

        return self.default_output_directory

    def get_mnh(
        self,
        mnt: rio.DatasetReader,
        mns: rio.DatasetReader,
        maille: pd.Series,
        resampling: Resampling = Resampling.bilinear,
        clip_height: bool = True,
    ) -> ma.MaskedArray:
        """Dériver le MNH d'une maille sur base des données MNT et MNS.

        :param mnt: Modèle numérique de terrain.
        :type mnt: rio.DatasetReader
        :param mns: Modèle numérique de surface.
        :type mns: rio.DatasetReader
        :param maille: Maille sur laquelle le MNH doit être calculé.
        :type maille: pd.Series
        :param resampling: Méthode de rééchantillonnage pour les avoir les données du
            MNT et MNS à la même résolution spatiale. Par défaut: Resampling.bilinear
        :type resampling: Resampling, optional
        :param clip_height: Si True (par défaut), les données du MNH sont bornées entre
            -5 et 25.
        :type clip_height: bool, optional
        :return: Modèle numérique de hauteur.
        :rtype: ma.MaskedArray
        """

        def get_mn_data_as_ma(
            mn: rio.DatasetReader,
            maille_gdf: gpd.GeoDataFrame,
            out_shape: Tuple[int, int, int],
            resampling: Resampling = Resampling.bilinear,
        ) -> ma.MaskedArray:
            maille_mn_window = geometry_window(mn, [maille_gdf.to_crs(mn.crs).geometry])
            maille_mn_data = mn.read(
                window=maille_mn_window, out_shape=out_shape, resampling=resampling
            )
            return ma.masked_equal(maille_mn_data, mn.nodata)

        # Les MNS photogrammétriques de 2019 et 2020 ont une plus grande résolution que
        # celui de 2018, ainsi que des MNS et MNT LIDAR de 2013 (0.5m vs. 1m), alors que
        # ces derniers sont plus précis. On utilise donc la résolution commune de 1m
        # pour dériver le MNH.
        maille_geom = gpd.GeoDataFrame(geometry=[maille.geometry], crs=maille.EPSG)
        out_shape = (1, maille.IMG_HEIGHT, maille.IMG_WIDTH)

        # Extraction des données MNT pour la maille
        maille_mnt_data = get_mn_data_as_ma(mnt, maille_geom, out_shape, resampling)

        # Extraction des données MNS pour la maille
        maille_mns_data = get_mn_data_as_ma(mns, maille_geom, out_shape, resampling)

        # Le MNS est borné pour éviter les valeurs négatives
        maille_mns_data = np.clip(maille_mns_data, a_min=0, a_max=999)

        # Calcul du MNH = MNS - MNT
        self.logger.debug("Calcul du MNH")
        maille_mnh_data = maille_mns_data - maille_mnt_data

        if clip_height:
            # Les valeurs du MNH sont bornées entre [-5 et 25]
            maille_mnh_data = np.clip(maille_mnh_data, -5, 25)

        return maille_mnh_data

    def get_ortho(self, ortho_dir: str, maille: pd.Series) -> Raster_data_meta:
        """Extraire les données des orthophotos.

        :param ortho_dir: Dossier contenant les orthophotos et suivant l'arborescence
            définie par l'argument `folder_structure` de la configuration.
        :type ortho_dir: str
        :param maille: Maille pour laquelle les données doivent être extraites.
        :type maille: pd.Series
        :return: Tuple contenant les données de l'orthophoto et les métadonnées
            associées.
        :rtype: Raster_data_meta
        """
        # Détermination du path vers le fichier orthophoto
        ortho_filepath = filepath.get_filepath(
            dir=ortho_dir,
            folder_structure=self.config["folder_structure"],
            maille=maille,
            mkdir=False,
        )

        # Lecture de l'orthophoto
        self.logger.debug(f"Lecture de l'orthophoto ({ortho_filepath})")
        with rio.open(ortho_filepath) as ortho:
            maille_ortho_data = ortho.read()
            maille_ortho_data = ma.masked_equal(maille_ortho_data, ortho.nodata)
            maille_ortho_meta = ortho.meta

        # Vérification de la conformité de l'orthophoto: 4 bandes spectrales
        # Pas possible de vérifier l'ordre cependant
        assert maille_ortho_meta["count"] == 4, (
            f"L'orthophoto ({ortho_filepath}) doit contenir les 4 bandes suivantes, "
            "dans l'ordre: rouge, vert, bleu, et infra-rouge."
        )

        return maille_ortho_data, maille_ortho_meta
