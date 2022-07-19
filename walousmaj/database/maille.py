"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour la gestion de la base de données des mailles.
"""
from typing import Dict, List, Union

import geopandas as gpd
import pandas as pd

from walousmaj.database import crud
from walousmaj.utils.enums import StageOrder, Status

TABLE_NAME = "maille"


def create_database() -> None:
    """Créer la base de données regroupant les mailles et leur statut respectif."""
    schema = """
        IMAGE_NAME   VARCHAR,
        OBJECTID     VARCHAR,
        stage        VARCHAR,
        status       VARCHAR,
        error        VARCHAR,
        last_update  TIMESTAMP DEFAULT (DATETIME('NOW', 'localtime'))"""
    crud.create_database(TABLE_NAME, schema)
    trigger_statement = (
        "CREATE TRIGGER walous_update_maille_trigger AFTER UPDATE OF stage, status ON "
        + TABLE_NAME
        + " BEGIN update "
        + TABLE_NAME
        + " SET last_update = DATETIME('NOW', 'localtime') "
        "WHERE IMAGE_NAME = new.IMAGE_NAME;"
        " END;"
    )
    crud.execute_sql_statement(trigger_statement)


def populate_database(
    maillage_df: Union[pd.DataFrame, gpd.GeoDataFrame],
    stage_default: str = StageOrder.INITIALIZATION.value,
    status_default: str = Status.DONE.value,
) -> None:
    """Populer la base de données des mailles sur base d'un DataFrame.

    :param maillage_df: DataFrame source de données.
    :type maillage_df: Union[pd.DataFrame, gpd.GeoDataFrame]
    :param stage_default: Stage par défaut à assigner à chaque maille pour
        l'initialisation. Défaut: StageOrder.INITIALIZATION.value
    :type stage_default: str, optional
    :param status_default: Statut par défaut à assigner à chaque maille pour
        l'initialisation. Défaut: Status.DONE.value
    :type status_default: str, optional
    """
    df = maillage_df.loc[:, ["IMAGE_NAME", "OBJECTID"]]
    df["status"] = status_default
    df["stage"] = stage_default
    df["error"] = ""
    crud.populate_database_from_dataframe(TABLE_NAME, df)


def update(
    mailles: Union[
        pd.Series, gpd.GeoSeries, gpd.GeoDataFrame, List[pd.Series], List[gpd.GeoSeries]
    ],
    **new_values: Dict[str, str],
) -> None:
    """Mettre à jour une ou plusieurs mailles.

    :param mailles: Maille(s) à mettre à jour. Doit contenir l'attribut `IMAGE_NAME`.
    :type mailles: Union[ pd.Series, gpd.GeoSeries, gpd.GeoDataFrame, List[pd.Series], List[gpd.GeoSeries] ]
    :param new_values: Dictionnaire reprenant les paires attributs[key]-valeurs[value]
        à mettre à jour pour la/les maille(s).
    :type new_values: Dict[str, str]
    :raises ValueError: Si le type de l'argument `mailles` n'est pas pris en charge.
    """
    if isinstance(mailles, gpd.GeoDataFrame):
        mailles = [m for _, m in mailles.iterrows()]
    elif isinstance(mailles, (pd.Series, gpd.GeoSeries)):
        mailles = [mailles]
    elif not isinstance(mailles, list):
        raise ValueError(f"Unexpected _mailles_ type: {type(mailles)}")
    mailles = [m["IMAGE_NAME"] for m in mailles]
    new_values_formatted = ", ".join([f"{k}='{v}'" for k, v in new_values.items()])
    sql_statement = (
        f"UPDATE {TABLE_NAME} SET {new_values_formatted} WHERE IMAGE_NAME LIKE "
    )
    if len(mailles) == 1:
        update_one_maille(mailles[0], sql_statement)
    else:
        update_many_mailles(mailles, sql_statement)


def update_one_maille(maille: str, sql_statement: str) -> None:
    """Mise à jour d'une maille sur base d'une commande SQL déjà préformée.

    :param maille: Maille à mettre à jour: `IMAGE_NAME`
    :type maille: str
    :param sql_statement: Commande SQL.
    :type sql_statement: str
    """
    crud.execute_sql_statement(sql_statement + f"'{maille}'")


def update_many_mailles(mailles: List[str], sql_statement: str) -> None:
    """Mise à jour de plusieurs mailles sur base d'une commande SQL déjà préformée.

    :param mailles: Mailles à mettre à jour: `IMAGE_NAME`
    :type mailles: List[str]
    :param sql_statement: Commande SQL.
    :type sql_statement: str
    """
    crud.executemany_sql_statement(sql_statement + "(?)", [(m,) for m in mailles])
