"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour la gestion de la base de données des stages.
"""
from typing import TYPE_CHECKING, Dict

import pandas as pd

from walousmaj.database import crud
from walousmaj.utils.enums import StageOrder, Status

if TYPE_CHECKING:
    from walousmaj.core import Pipeline

TABLE_NAME = "stage"


def create_database() -> None:
    """Créer la base de données regroupant les stages."""
    schema = """
        position        INTEGER,
        stage           VARCHAR,
        status          VARCHAR,
        progress        VARCHAR,
        remaining_time  VARCHAR,
        last_update     TIMESTAMP DEFAULT (DATETIME('NOW', 'localtime'))"""
    crud.create_database(TABLE_NAME, schema)
    trigger_statement = (
        "CREATE TRIGGER walous_update_stage_trigger AFTER UPDATE "
        "OF stage, status, progress, remaining_time ON "
        + TABLE_NAME
        + " BEGIN update "
        + TABLE_NAME
        + " SET last_update = DATETIME('NOW', 'localtime') "
        "WHERE stage = new.stage;"
        " END;"
    )
    crud.execute_sql_statement(trigger_statement)


def populate_database(
    pipeline: "Pipeline", status_default: Status = Status.PENDING.name
) -> None:
    """Populer la table des stages sur base d'une `Pipeline`.

    :param pipeline: Pipeline définissant les différents stages et leur ordre.
    :type pipeline: Pipeline
    :param status_default: Statut par défaut à assigner à chaque stage pour
        l'initialisation. Défaut: Status.PENDING.name
    :type status_default: Statut, optional
    """
    data = [(x.position, x.name) for x in pipeline.stages]
    df = pd.DataFrame(data, columns=["position", "stage"])
    df["status"] = status_default
    df["progress"] = ""
    df["remaining_time"] = ""
    crud.populate_database_from_dataframe(TABLE_NAME, df)


def update(stage: str, **new_values: Dict[str, str]) -> None:
    """Mettre à jour un stage.

    :param stage: Stage à mettre à jour.
    :type stage: str
    :param new_values: Dictionnaire reprenant les paires attributs[key]-valeurs[value]
        à mettre à jour pour le stage.
    :type new_values: Dict[str, str]
    """
    new_values_formatted = ", ".join([f"{k}='{v}'" for k, v in new_values.items()])
    sql_statement = (
        f"UPDATE {TABLE_NAME} SET {new_values_formatted} WHERE stage LIKE '{stage}'"
    )
    crud.execute_sql_statement(sql_statement)


def get_last_successful_stage() -> StageOrder:
    """Obtenir le dernier stage réussi.

    :return: Dernier stage réussi.
    :rtype: StageOrder
    """
    data = crud.get_data(TABLE_NAME, ["position", "stage", "status"])
    latest_ss = 0
    for stage in data:
        if stage["status"] == Status.DONE.name and stage["position"] > latest_ss:
            latest_ss = stage["position"]
    return list(StageOrder)[latest_ss]
