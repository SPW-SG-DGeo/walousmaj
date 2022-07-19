"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour la gestion de la base de données des jobs.
"""
from sqlite3 import OperationalError
from typing import Dict

from walousmaj.database import crud
from walousmaj.utils.enums import Status

TABLE_NAME = "job"


def create_database(if_exist_ok: bool = True) -> None:
    """Créer la base de données regroupant les jobs.

    :param if_exist_ok: Paramètre pour éviter les conflits si la table existe déjà dans
        la base de données. Si True, alors l'éventuelle table en conflit sera supprimée
        et une nouvelle sera créée.
    :type job_id: bool, optional
    """
    schema = """
        id                      INTEGER PRIMARY KEY,
        job_id                  VARCHAR,
        start                   TIMESTAMP DEFAULT (DATETIME('NOW', 'localtime')),
        end                     TIMESTAMP,
        status                  VARCHAR,
        config_filepath         VARCHAR,
        job_directory           VARCHAR,
        last_successful_stage   INTEGER,
        input_queue             VARCHAR"""
    crud.create_database(TABLE_NAME, schema, if_exist_ok)


def insert(
    job_id: str,
    config_filepath: str,
    job_directory: str,
    status_default: Status = Status.ONGOING.name,
) -> None:
    """Insérer des données dans la table des jobs.

    :param job_id: ID du job.
    :type job_id: str
    :param config_filepath: Chemin vers le fichier de configuration propre au job.
    :type config_filepath: str
    :param job_directory: Chemin vers le dossier du job.
    :type job_directory: str
    :param status_default: Statut à donner au job. Défaut: Status.ONGOING.name
    :type status_default: Statut, optional
    """
    sql_statement = (
        f"INSERT INTO {TABLE_NAME}(job_id, config_filepath, job_directory, status) VALUES "
        f"('{job_id}', '{config_filepath}', '{job_directory}', '{status_default}')"
    )
    crud.execute_sql_statement(sql_statement)


def update(job_id: str, **new_values: Dict[str, str]) -> None:
    """Mettre à jour une entrée dans la base de données des jobs.

    :param job_id: ID du job à mettre à jour.
    :type job_id: str
    :param new_values: Dictionnaire reprenant les paires attributs[key]-valeurs[value]
        à mettre à jour pour le job.
    :type new_values: Dict[str, str]
    """
    new_values_formatted = ", ".join([f'{k}="{v}"' for k, v in new_values.items()])
    sql_statement = (
        f"UPDATE {TABLE_NAME} SET {new_values_formatted} WHERE job_id LIKE '{job_id}'"
    )
    crud.execute_sql_statement(sql_statement)


def get_last_job() -> Dict[str, str]:
    """Obtenir les données correspondant au dernier job.

    :return: Dictionnaire reprenant les paires attributs[key]-valeurs[value] du dernier
        job.
    :rtype: Dict[str, str]
    """
    sql_statement = f"SELECT * FROM {TABLE_NAME} ORDER BY start desc LIMIT 1"
    try:
        values = crud.execute_sql_statement(sql_statement)[0]
    except OperationalError:
        return {}
    attributes = [
        "id",
        "job_id",
        "start",
        "end",
        "status",
        "config_filepath",
        "job_directory",
        "last_successful_stage",
        "input_queue",
    ]
    return dict(zip(attributes, values))
