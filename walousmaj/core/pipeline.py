"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Definition de la classe Pipeline.
"""
from datetime import datetime
from logging import Logger
from pathlib import Path
from shutil import copy, rmtree
from typing import TYPE_CHECKING, List, Union

from walousmaj.database import job as job_db
from walousmaj.utils.enums import StageOrder, Status
from walousmaj.utils.permissions import update_permissions
from walousmaj.utils.typing import Config

if TYPE_CHECKING:
    from walousmaj.core import Stage


class Pipeline:
    """Classe Pipeline regroupant les différents `Stages` pour l'execution d'un job."""

    def __init__(
        self, stages: List["Stage"], config: Config, resume: bool, logger: Logger
    ):
        """Pipeline regroupant les différents `Stages` pour l'execution d'un job.

        Cette classe fait office de chef d'orchestre lors de l'exécution d'un job. Elle
        gère l'ordre d'exécution des différents `Stages` et la passation des données
        entre eux.

        :param stages: Liste de `Stages` à considérer pour l'exécution. Leur ordre dans
            la liste détermine leur ordre d'exécution.
        :type stages: List[Stage]
        :param config: Paramètres configurant l'exécution du job.
        :type config: Config
        :param resume: Choix sur la reprise de l'exécution précédente ou non. En mode
            `Resume`, l'exécution reprendra là où elle s'était interrompue lors du
            précédent job.
        :type resume: bool
        :param logger: Instance d'un `Logger`.
        :type logger: Logger
        """
        self.config = config
        self.logger = logger
        self.input_queue = []  # Liste de données d'entrée pour le prochain stage
        self.stages = [stage(self.logger) for stage in stages]
        self.resume = resume

    def __call__(self) -> None:
        """Exécuter la `Pipeline`."""
        job_start = datetime.now()
        self.logger.info(
            f"Execution démarrée à {job_start.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.logger.info(
            f"Stages considérés:\n{' -> '.join([stage.name for stage in self.stages])}"
        )
        self.logger.info(f"Configuration pre-initialisation:\n{self.config}")
        for stage in self.stages:
            self.logger.info(f"{stage.position} - {stage.name}")

            # Vérification de la nécessité de l'étape
            skip_phase_from_config = self.config.get(stage.name.lower(), {}).get("skip")
            if skip_phase_from_config:
                self.logger.info(
                    "Cette étape a été sautée en accord avec la configuration"
                )
                stage.update_skipped_status(self.config["job_id"])
                continue

            if stage.stage_order == StageOrder.INITIALIZATION:
                # Cas particulier pour le premier Stage Initialization
                maillage, self.config, self.input_queue = stage(self, self.config)
                self.logger.info(f"Configuration post-initialisation:\n{self.config}")
                self.logger.info(f"Mode resume: {self.resume}")
                if self.resume:
                    # Si en mode Resume/Reprise, determination du stage auquel reprendre
                    # l'exécution
                    failed_stage = list(StageOrder)[
                        self.config["last_successful_stage"] + 1
                    ]
                    self.logger.info(f"Reprise à l'étape #{failed_stage}")
            elif stage.position > self.config["last_successful_stage"]:
                output_filepath_directory = stage(
                    self.config, input_queue=self.input_queue, maillage=maillage
                )
                self.maintain_queue(stage, output_filepath_directory)
            else:
                # Les étapes déjà réussies sont sautées (mode Resume/Reprise)
                stage.update_skipped_status(self.config["job_id"])
                self.logger.info(
                    f"Cette étape #{stage.position} a été sautée car la dernière étape "
                    f"réussie est l'étape #{self.config['last_successful_stage']}"
                )

        # Sauvegarde des données de sortie dans l'`output_directory` et nettoyage des
        # données temporaires
        self.save_output()
        rmtree(self.config["job_directory"])

        # Détermination du temps d'exécution
        job_end = datetime.now()
        job_db.update(
            self.config["job_id"],
            status=Status.DONE.name,
            end=job_end.strftime("%Y-%m-%d %H:%M:%S"),
        )
        elapsed_time = (job_end - job_start) / 60
        self.logger.info(
            "Execution terminée avec succès à "
            f"{job_end.strftime('%Y-%m-%d %H:%M:%S')} en {elapsed_time} minute(s)."
        )

    def save_output(self) -> None:
        """Sauvegarder les données de sortie dans l'`output_directory` défini dans le
        fichier de configuration."""
        self.logger.info("Sauvegarde des données de sortie")
        dst_dir = Path(self.config["output_directory"])
        dst_dir.mkdir(parents=True, exist_ok=True)
        basename = self.config["output_filename"]

        # Sauvegarde des données de sortie
        for src_fp in self.input_queue:
            ext = src_fp.suffix
            suffix = "_ChangeMap" if src_fp.stem.endswith("_cm") else ""
            dst_fp = dst_dir / (basename + suffix + ext)
            self.logger.debug(f"Copie du fichier {src_fp} --> {dst_fp}")
            copy(src_fp, dst_fp)

        # Sauvegarde du fichier de configuration et de maillage
        for key in ["config_filepath", "maillage_filepath"]:
            src_fp = Path(self.config[key])
            dst_fp = dst_dir / (basename + "_" + src_fp.name)
            self.logger.debug(f"Copie du fichier {src_fp} --> {dst_fp}")
            copy(src_fp, dst_fp)

        # Changements des permissions
        update_permissions(directory=str(dst_dir))

    def maintain_queue(self, stage: "Stage", elements: Union[List[str], str]) -> None:
        """Maintenir à jour l'`input_queue`.

        Cette méthode permet de mettre à jour la liste des données d'entrée du `Stage` suivant en fonction des données de sortie du `Stage` précédent.

        :param stage: Stage dont l'exécution vient de se terminer et dont les `elements`
            sont dérivés.
        :type stage: Stage
        :param elements: Données de sortie du `stage`.
        :type elements: Union[List[str], str]
        """
        if stage.consumer:
            self.input_queue = []
        if isinstance(elements, (str, Path)):
            elements = [elements]
        self.input_queue.extend(elements)
        job_db.update(
            self.config["job_id"], input_queue=str(list(map(str, self.input_queue)))
        )
