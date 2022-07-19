"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Inference.
"""
import argparse
from logging import Logger
from typing import Any, Dict, List

import numpy as np
import rasterio as rio
import torch
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer
from detectron2.projects.deeplab import add_deeplab_config

from walousmaj.core import Stage
from walousmaj.core.stages.inference.datamapper import GeoDatasetMapper
from walousmaj.utils import mappings
from walousmaj.utils.enums import StageOrder
from walousmaj.utils.tempkeys import get_template_keys
from walousmaj.utils.window import iter_windows_with_overlap as iwindows


class Inference(Stage):
    """Inférence du modèle sur les données (Ortho + MNH).

    Stage se chargeant de l'inférence du modèle et de la conversion des données de
    sortie du modèle en prédictions.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.INFERENCE, logger)

    def execute(self, stage_config: Dict[str, Any]):
        # Traitement des arguments
        self.logger.debug("Traitement des arguments")
        args = argparse.Namespace()
        args.config_file = stage_config["model_config_filepath"]
        args.dist_url = "tcp://127.0.0.1:50154"
        args.eval_only = True
        args.machine_rank = 0
        args.num_gpus = 1
        args.num_machines = 1
        args.opts = []
        args.resume = False
        return self.infer(args, stage_config)

    def infer(self, args, stage_config):
        # Mapping de décodage des données des sortie
        decoding_cmap = mappings.to_mapping_array(mappings.models_to_ocs_labels())

        # Initialisation du modèle
        self.logger.debug("Initialisation du modèle avec les arguments:")
        self.logger.debug(args)
        cfg = self.setup(args)
        model = DefaultTrainer.build_model(cfg)
        model.eval()  # Conversion du modèle en mode Evaluation
        DetectionCheckpointer(model).load(cfg.MODEL.WEIGHTS)  # Chargements des poids
        self.logger.info(f"Utilisation des poids du fichier {cfg.MODEL.WEIGHTS}")

        # Initialisation du mapper de données et de l'itérateur de données
        self.logger.debug("Initialisation du mapper et de l'itérateur de données")
        mapper = GeoDatasetMapper(is_train=False, augmentations=[], image_format=None)
        iterator_data_dicts = self.get_data_dicts()

        for img_dict in self.iterate(iterator_data_dicts):
            self.logger.info(f"Inférence de la maille {img_dict['IMAGE_NAME']}")

            # Détermination du chemin vers le fichier des données de sortie
            output_fp = self.get_output_filepath(maille=img_dict)

            # Extraction des métadonnées des données d'entrée et adaptation en
            # métadonnées de sortie
            with rio.open(img_dict["file_name"]) as input_raster:
                meta = input_raster.meta
            meta.update(
                {"count": 1, "dtype": "uint8", "nodata": stage_config["output_nodata"]}
            )

            # Initialisation de l'itérateur pour les vignettes
            windows_iterator = iwindows(
                input_height=img_dict["IMG_HEIGHT"],
                input_width=img_dict["IMG_WIDTH"],
                window_size=cfg.INPUT.MIN_SIZE_TEST,
                overlap=stage_config["overlap"],
            )

            with rio.open(output_fp, "w", compress="lzw", **meta) as output_raster:
                while True:  # Tant qu'il y a encore des vignettes pour la maille
                    img_dict_list = []
                    stop_iteration_flag = False

                    # Construction du batch en stackant les vignettes
                    self.logger.debug("Génération du batch")
                    for _ in range(cfg.SOLVER.IMS_PER_BATCH):
                        try:
                            iter_out = next(windows_iterator)
                            window_read, window_write, pred_slice = iter_out
                            kwargs = {
                                "window_write": window_write,
                                "pred_slice": pred_slice,
                            }
                            img_dict_list.append(
                                mapper(img_dict, window_read, **kwargs)
                            )
                        except StopIteration:
                            stop_iteration_flag = True
                    curr_batch_size = len(img_dict_list)
                    if curr_batch_size > 0:
                        # Inférence
                        self.logger.debug("Inférence et sauvegarde")
                        with torch.set_grad_enabled(False):
                            # outputs.shape = IMS_PER_BATCH x NUM_CLASSES x
                            # MIN_SIZE_TEST x MIN_SIZE_TEST
                            outputs = model(img_dict_list)
                            for i, output in enumerate(outputs):
                                # Extraction et traitement des prédictions
                                predictions = self.sem_seg_to_predictions(
                                    sem_seg=output["sem_seg"],
                                    decoding_cmap=decoding_cmap,
                                    src_nodata=img_dict_list[i]["nodata"],
                                    dst_nodata=stage_config["output_nodata"],
                                    slices=img_dict_list[i]["pred_slice"],
                                )

                                # Sauvegarde des prédictions.
                                output_raster.write(
                                    predictions,
                                    window=img_dict_list[i]["window_write"],
                                    indexes=1,
                                )
                    if stop_iteration_flag:
                        break

        return self.default_output_directory

    def get_data_dicts(self) -> List[Dict[str, Any]]:
        """Créer une liste de `dataset_dicts` regroupant les informations relatives à
        une maille."""
        dataset_dicts = []
        for _, maille in self.maillage.iterrows():
            record = {}
            record["file_name"] = self.get_input_filepath(maille=maille)
            record["IMAGE_NAME"] = maille.IMAGE_NAME
            record["IMG_HEIGHT"] = maille.IMG_HEIGHT
            record["IMG_WIDTH"] = maille.IMG_WIDTH
            record["height"] = 512
            record["width"] = 512
            for keys in get_template_keys(self.config["folder_structure"]):
                record[keys] = maille[keys]
            dataset_dicts.append(record)
        return dataset_dicts

    @staticmethod
    def sem_seg_to_predictions(sem_seg, decoding_cmap, src_nodata, dst_nodata, slices):
        """Conversion de l'output du model en prédictions."""
        # predictions.shape = IMS_PER_BATCH x MIN_SIZE_TEST x MIN_SIZE_TEST
        predictions = sem_seg.argmax(dim=0)
        predictions = predictions.cpu().detach().numpy()

        # Conversion des prédictions en labels WalOUS_OCS
        predictions = decoding_cmap[predictions.astype("uint8")]

        # Traitement des nodata dans les données d'entrée
        predictions = np.where(src_nodata, predictions, dst_nodata)

        # Decoupage des prédictions pour tenir compte du chevauchement des vignettes
        predictions = predictions[slices]

        return predictions.astype("uint8")

    @staticmethod
    def setup(args):
        """Créer la configuration et initialisation de base."""
        cfg = get_cfg()
        add_deeplab_config(cfg)
        cfg.merge_from_file(args.config_file)
        return cfg
