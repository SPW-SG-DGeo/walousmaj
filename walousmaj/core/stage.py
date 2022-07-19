"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Classe de base abstraite pour définir un Stage.
"""
import shlex
from abc import ABC, abstractmethod
from copy import deepcopy
from functools import lru_cache
from logging import Logger
from pathlib import Path
from subprocess import check_call
from time import time
from typing import Any, Dict, Generator, Iterator

import geopandas as gpd
from walousmaj.database import job as job_db
from walousmaj.database import maille as maille_db
from walousmaj.database import stage as stage_db
from walousmaj.exceptions import WalousMaJError
from walousmaj.utils import filepath
from walousmaj.utils.enums import StageOrder, StageOutputType, Status
from walousmaj.utils.permissions import update_permissions
from walousmaj.utils.typing import Config, Input_queue, Maille, Output_queue


class Stage(ABC):
    """Classe de base abstraite pour définir un Stage."""

    def __init__(
        self,
        stage_order: StageOrder,
        logger: Logger,
        consumer: bool = True,
        output_type: StageOutputType = StageOutputType.DIRECTORY,
    ) -> None:
        """Initialiser une instance de la classe.

        :param stage_order: Définition de l'ordre/position du stage.
        :type stage_order: StageOrder
        :param logger: Logger à greffer au stage.
        :type logger: Logger
        :param consumer: Déterminer si le stage doit se comporter comme un `consumer`
            ou non. Un `consumer` consomme les données de l'`input_queue` et les
            remplace par de nouvelles. Défaut: `consumer`
        :type consumer: bool, optional
        :param output_type: Type d'output du stage (fichier ou dossier). Défaut:
            StageOutputType.DIRECTORY
        :type output_type: StageOutputType, optional
        """
        self.stage_order = stage_order
        self.name = self.stage_order.name
        self.position = self.stage_order.value
        self.consumer = consumer
        self.output_type = output_type
        self.maillage: gpd.GeoDataFrame = None
        self.logger = logger
        self.processed_mailles = None

    def __call__(
        self,
        config: Config,
        input_queue: Input_queue,
        maillage: gpd.GeoDataFrame,
        *args: Any,
        **kwds: Any,
    ) -> Output_queue:
        """Exécution du stage.

        Méthode parente appelée lors de l'exécution du stage responsable pour appeler la méthode abstraite "execute" implémentée dans chaque stage. Elle est également responsable pour attraper les éventuelles erreurs.

        :param config: Configuration du job.
        :type config: Config
        :param input_queue: Liste regroupant les inputs qui doivent être pris en compte
            par le stage.
        :type input_queue: Input_queue
        :param maillage: Ensemble des mailles à considérer.
        :type maillage: gpd.GeoDataFrame
        :return: Retourne le résultat de la méthode abstraite "execute" implémentée dans
            le stage.
        :rtype: Output_queue
        """
        self.config = config
        self.input_queue = input_queue
        self.maillage = maillage
        self.total_mailles = len(self.maillage.index)
        self.processed_mailles = deepcopy(self.maillage)
        self.update_pending_mailles()
        self.update_ongoing_status(progress=0)
        try:
            stage_config = self.config.get(self.name.lower(), {})
            stage_config.pop("skip", None)
            self.logger.debug(f"Configuration propre à la phase:\n{stage_config}")
            out = self.execute(stage_config, *args, **kwds)
            self.update_done_status()
            return out
        except Exception as e:
            self.logger.error("Une exception est survenue:", exc_info=True)
            e_stage = WalousMaJError(stage=self.stage_order, message=e.__repr__())
            # Mise à jour des permissions sur les fichiers temporaires
            update_permissions(directory=str(self.config["job_directory"]))
            # Mise à jour des bases de données
            self.update_error_mailles(str(e_stage))
            self.update_error_status()
            self.update_error_job()
            raise e_stage from e

    @abstractmethod
    def execute(self, stage_config: Config) -> Output_queue:
        """Méthode à implémenter pour chacun des stages et qui lui est spécifique."""

    def call_cmd(self, cmd: str) -> None:
        """Exécute une ligne de commande.

        Typiquement une commande GDAL.

        :param cmd: Commande à exécuter.
        :type cmd: str
        """
        self.logger.debug(f"Commande gdal: {cmd}")

        # Execution de la commande gdal
        check_call(shlex.split(cmd))

    def iterate(
        self, iterator: Iterator, batch_size: int = 1, update_db: bool = True
    ) -> Generator[Any, None, None]:
        """Itérer sur un `iterator` par batch tout en mettant à jour la base de données des mailles.

        :param iterator: Itérator sur lequel itérer
        :type iterator: Iterator
        :param batch_size: Taille d'un batch pour regourper plusieurs données lors de
            chaque itération. Défaut: 1.
        :type batch_size: int, optional
        :param update_db: Maintenir ou non la base de données de mailles à jour.
            Défaut: True.
        :type update_db: bool, optional
        :yield: Un batch par itération
        :rtype: Generator[Any, None, None]
        """
        self.processed_mailles = []
        start_time = time()
        for i, maille in enumerate(iterator, start=1):
            self.processed_mailles.append(maille)
            if len(self.processed_mailles) == batch_size:
                if batch_size == 1:
                    iter_ = deepcopy(self.processed_mailles[0])
                else:
                    iter_ = deepcopy(self.processed_mailles)
                if update_db:
                    self.update_ongoing_mailles()
                yield iter_
                if update_db:
                    self.update_done_mailles()
                    self.update_ongoing_status_iter(start_time, index=i)
                self.processed_mailles = []
        if len(self.processed_mailles) > 0:
            if update_db:
                self.update_ongoing_mailles()
            yield deepcopy(self.processed_mailles)
            if update_db:
                self.update_done_mailles()

    def iterate_maillage(
        self, batch_size: int = 1, update_db: bool = True
    ) -> Generator[Maille, None, None]:
        """Itérer sur le ficher de maillage.

        :param batch_size: _Taille d'un batch pour regourper plusieurs données lors de
            chaque itération. Défaut: 1.
        :type batch_size: int, optional
        :param update_db: Maintenir ou non la base de données de mailles à jour.
            Défaut: True.
        :type update_db: bool, optional
        :yield: Un batch de `batch_size` mailles.
        :rtype: Generator[Maille, None, None]
        """

        def maillage_iterator(maillage):
            for _, maille in maillage.iterrows():
                yield maille

        yield from self.iterate(maillage_iterator(self.maillage), batch_size, update_db)

    def get_output_path(self) -> Path:
        """Obtenir le chemin vers le fichier contenant la donnée de sortie."""
        if self.output_type == StageOutputType.DIRECTORY:
            return self.default_output_directory
        elif self.output_type == StageOutputType.FILE:
            return self.default_output_filepath()
        else:
            raise ValueError(
                f"L'`output_type` du `Stage` {self.name} n'est pas valide. "
                f"Attendu: {list(map(str, StageOutputType))} . Reçu: {self.output_type}"
            )

    @property
    @lru_cache()
    def default_output_directory(self) -> Path:
        """Obtenir le chemin vers le dossier contenant les données de sortie."""
        return Path(self.config["job_directory"]) / self.name.lower()

    def default_output_filepath(
        self, suffix: str = None, ext: str = ".tif", mkdir: bool = True
    ) -> Path:
        """Obtenir le chemin par défaut vers le fichier contenant la donnée de sortie.

        :param suffix: Suffix à utiliser pour générer le nom du fichier de sortie.
            Défaut: None.
        :type suffix: str, optional
        :param ext: Extension du fichier de sortie. Défaut: ".tif"
        :type ext: str, optional
        :param mkdir: Création du/des dossier(s) parent(s). Défaut: True.
        :type mkdir: bool, optional
        :return: Chemin ver le fichier de sortie.
        :rtype: Path
        """
        filename = self.name.lower()
        if suffix:
            filename += f"_{suffix}"
        filename += ext if ext.startswith(".") else f".{ext}"
        output_fp = self.default_output_directory / filename
        if mkdir:
            output_fp.parent.mkdir(parents=True, exist_ok=True)
        return output_fp

    def get_output_filepath(self, maille: Dict[str, str], mkdir: bool = True) -> Path:
        """Obtenir le chemin du fichier de sortie sur base d'une maille.

        :param maille: Maille à laquelle se rapporte le fichier de sortie.
        :type maille: Dict[str, str]
        :param mkdir: Création du/des dossier(s) parent(s). Défaut: True.
        :type mkdir: bool, optional
        :return: Chemin vers le fichier de sortie.
        :rtype: Path
        """
        return filepath.get_filepath(
            dir=self.default_output_directory,
            folder_structure=self.config["folder_structure"],
            maille=maille,
            mkdir=mkdir,
        )

    def get_input_filepath(self, maille: Dict[str, str]) -> Path:
        """Dériver le chemin vers le fichier d'entrée pour une maille.

        :param maille: Maille pour laquelle le fichier d'entrée doit être retrouvé.
        :type maille: Dict[str, str]
        :return: Chemin vers le fichier d'entrée.
        :rtype: Path
        """
        assert len(self.input_queue) == 1
        return filepath.get_filepath(
            dir=self.input_queue[0],
            folder_structure=self.config["folder_structure"],
            maille=maille,
            mkdir=False,
        )

    def _update_mailles(self, status: Status, **kwds: Any) -> None:
        """Mettre à jour les mailles traitées."""
        maille_db.update(self.processed_mailles, status=status.name, **kwds)

    def update_pending_mailles(self) -> None:
        """Mettre à jour les mailles traitées avec le statut `Pending`."""
        self._update_mailles(Status.PENDING, stage=self.name)

    def update_ongoing_mailles(self) -> None:
        """Mettre à jour les mailles traitées avec le statut `Ongoing`."""
        self._update_mailles(Status.ONGOING)

    def update_done_mailles(self) -> None:
        """Mettre à jour les mailles traitées avec le statut `Done`."""
        self._update_mailles(Status.DONE)

    def update_error_mailles(self, error_message: str) -> None:
        """Mettre à jour les mailles traitées avec le statut `Error`."""
        self._update_mailles(Status.ERROR, error=error_message)

    def _update_status(self, **kwds: Any) -> None:
        """Mettre à jour le statut d'un stage."""
        stage_db.update(self.name, **kwds)

    def update_ongoing_status(
        self, remaining_time: float = None, progress: float = None
    ) -> None:
        """Mettre à jour un stage avec le statut `Ongoing` et une indication de la progression."""
        kwds = {}
        if remaining_time:
            kwds["remaining_time"] = f"{remaining_time:6.2f} min"
        if progress:
            kwds["progress"] = f"{progress*100:4.2f}%"
        self._update_status(status=Status.ONGOING.name, **kwds)

    def update_error_status(self) -> None:
        """Mettre à jour un stage avec le statut `Error`."""
        self._update_status(status=Status.ERROR.name)

    def update_skipped_status(self, job_id: str) -> None:
        """Mettre à jour un stage avec le statut `Skipped` et mise à jour du
        `last_successful_stage`."""
        self._update_status(status=Status.SKIPPED.name)
        job_db.update(job_id, last_successful_stage=self.position)

    def update_done_status(self) -> None:
        """Mettre à jour un stage avec le statut `Done` et mise à jour du
        `last_successful_stage`."""
        self._update_status(
            status=Status.DONE.name, remaining_time="0 min", progress="100%"
        )
        job_db.update(self.config["job_id"], last_successful_stage=self.position)

    def update_ongoing_status_iter(self, start_time: float, index: int) -> None:
        """Mettre à jour un stage avec le statut `Ongoing` et une indication de la progression."""
        progress = index / self.total_mailles
        elapsed_mintues = (time() - start_time) / 60
        remaining_time = (elapsed_mintues / progress) - elapsed_mintues
        self.update_ongoing_status(remaining_time=remaining_time, progress=progress)

    def update_error_job(self) -> None:
        """Mettre à jour un job avec le statut `Error`."""
        job_db.update(self.config["job_id"], status=Status.ERROR.name)
