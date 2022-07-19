"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Stage: Initialization.
"""
from logging import Logger
from pathlib import Path
from shutil import rmtree
from typing import List
from uuid import uuid4

import geopandas as gpd
from pydantic import ValidationError
from shapely.ops import unary_union
from walousmaj.core import Pipeline, Stage
from walousmaj.database import job as job_db
from walousmaj.database import maille as maille_db
from walousmaj.database import stage as stage_db
from walousmaj.exceptions import WalousMaJError
from walousmaj.utils.enums import StageOrder, Status
from walousmaj.utils.filepath import parse_input_queue
from walousmaj.utils.permissions import update_permissions
from walousmaj.utils.typing import Config
from walousmaj.utils.validators import ConfigValidator
from yaml import Dumper, Loader, dump, load

DEFAULT_LAST_SUCCESSFUL_STAGE = StageOrder.RESTART.value


class Initialization(Stage):
    def __init__(self, logger: Logger) -> None:
        super().__init__(StageOrder.INITIALIZATION, logger)

    def __call__(self, pipeline: Pipeline, config: Config):
        if not pipeline.resume:
            # Validation du fichier de configuration
            self.config = self.validate_config(
                config=config, stages=pipeline.stages, resume=pipeline.resume
            )
            stage_config = config["initialization"]

            # Vérification de la suppression des fichiers du dernier job
            last_job = job_db.get_last_job()
            if last_job:
                self.logger.info(f"Suppression du dossier du job {last_job['job_id']}")
                rmtree(last_job["job_directory"], ignore_errors=True)
            # Création d'un nouveau job
            job_id = str(uuid4())
            self.logger.debug(f"Job ID: {job_id}")
            job_dir = Path(self.config["workspace_directory"]) / job_id
            change_permissions_flag = not job_dir.parent.is_dir()
            job_dir.mkdir(parents=True, exist_ok=True)
            if change_permissions_flag:
                update_permissions(directory=str(job_dir.parent))
            config_filepath = job_dir / "config.yml"
            maillage = self.get_maillage(
                stage_config["maillage_filepath"],
                stage_config.get("mailles"),
                stage_config.get("aoi_filepath"),
            )
            if len(maillage.index) == 0:
                raise WalousMaJError(
                    stage=StageOrder.INITIALIZATION, message="Aucune maille trouvée."
                )
            maillage_filepath = job_dir / "maillage.shp"
            maillage.to_file(maillage_filepath)
            input_queue = []
            self.config.update(
                {
                    "job_id": job_id,
                    "job_directory": str(job_dir),
                    "config_filepath": str(config_filepath),
                    "maillage_filepath": str(maillage_filepath),
                    # Pour ne sauter aucune étape, en mode normal, le
                    # last_successful_stage est mis à RESTART (la valeur la plus basse)
                    "last_successful_stage": DEFAULT_LAST_SUCCESSFUL_STAGE,
                }
            )
            with config_filepath.open("w") as f:
                dump(self.config, f, Dumper=Dumper)

            self.initialize_stage_database(pipeline)
        else:  # Mode Resume/Reprise
            # Récupération des données du dernier job
            job_data = job_db.get_last_job()
            if not job_data:
                raise WalousMaJError(
                    stage=StageOrder.INITIALIZATION,
                    message="Aucun job trouvé pour lancer une exécution en mode `resume`.",
                )
            job_id = job_data["job_id"]
            job_dir = job_data["job_directory"]
            self.logger.debug(f"Continue avec job_id {job_id} et data:\n{job_data}")
            config_filepath = Path(job_data["config_filepath"])
            self.config = load(config_filepath.read_bytes(), Loader=Loader)
            self.config["resume"] = True
            self.config["last_successful_stage"] = job_data["last_successful_stage"]
            stage_config = self.config["initialization"]
            maillage = self.get_maillage(
                stage_config["maillage_filepath"],
                stage_config.get("mailles"),
                stage_config.get("aoi_filepath"),
            )
            input_queue = parse_input_queue(job_data["input_queue"])

        self.initialize_maille_database(maillage)
        self.initialize_job_database(
            job_id, pipeline.resume, config_filepath, str(job_dir)
        )
        self.update_done_status()
        return maillage, self.config, input_queue

    def execute(self):
        pass

    @staticmethod
    def initialize_maille_database(maillage):
        maille_db.create_database()
        maille_db.populate_database(maillage)

    @staticmethod
    def initialize_stage_database(pipeline):
        stage_db.create_database()
        stage_db.populate_database(pipeline)

    def initialize_job_database(
        self,
        job_id: str,
        resume: bool,
        config_filepath: str = None,
        job_directory: str = None,
    ):
        job_db.create_database()
        if resume:
            job_db.update(job_id, status=Status.ONGOING.name)
        else:
            job_db.insert(job_id, config_filepath, job_directory=job_directory)

    @staticmethod
    def validate_config(config: Config, stages: List[Stage], resume: bool) -> Config:
        try:
            return ConfigValidator(**config).dict()
        except ValidationError as e:
            raise ValueError(f"Le fichier de configuration n'est pas valide: {e}")

    def get_maillage(
        self,
        maillage_filepath: str,
        mailles: List[str] = None,
        aoi_filepath: str = None,
    ) -> gpd.GeoDataFrame:
        maillage = gpd.read_file(maillage_filepath)
        self.logger.debug("Le maillage contient %s mailles", maillage.shape[0])
        if mailles:
            self.logger.debug(
                "Le maillage est filtré sur base des mailles suivantes: %s", mailles
            )
            maillage = maillage[maillage["IMAGE_NAME"].isin(mailles)]
            self.logger.debug("Le maillage contient %s mailles", maillage.shape[0])
        if aoi_filepath:
            self.logger.debug(
                "Le maillage est filtré sur base de la région d'intérêt définie dans: "
                f"{aoi_filepath}"
            )
            aoi = gpd.read_file(aoi_filepath).to_crs(maillage.crs)
            intersect_mask = maillage.intersects(unary_union(aoi.geometry))
            maillage = maillage[intersect_mask]
            self.logger.debug("Le maillage contient %s mailles", maillage.shape[0])
        return maillage
