"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour la gestion de bases de données.
"""
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import pandas as pd

from walousmaj import DB_FILEPATH


def create_database(table_name: str, schema: str, if_exist_ok: bool = False) -> None:
    """Créer une base de donnée et une table suivant un schéma.

    :param table_name: Nom à donner à la table.
    :type table_name: str
    :param schema: Schéma de la table.
    :type schema: str
    :param if_exist_ok: Paramètre pour éviter les conflits si la table existe déjà dans
        la base de données. Si True, alors l'éventuelle table en conflit sera supprimée
        et une nouvelle sera créée.
    :type if_exist_ok: bool, optional
    """
    Path(DB_FILEPATH).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_FILEPATH)) as con:
        cur = con.cursor()
        if not if_exist_ok:
            cur.execute("DROP TABLE IF EXISTS " + table_name)
        cur.execute("CREATE TABLE IF NOT EXISTS " + table_name + "(" + schema + ")")
        con.commit()


def execute_sql_statement(sql_statement: str) -> Union[List[List[str]], None]:
    """Exécuter une commande SQL.

    :param sql_statement: La commande SQL à exécuter.
    :type sql_statement: str
    :return: Les éléments retournés par la commande s'il s'agit d'un SELECT. None dans
        les autres cas.
    :rtype: Union[List[List[str]], None]
    """
    with closing(sqlite3.connect(DB_FILEPATH)) as con:
        cur = con.cursor()
        res = cur.execute(sql_statement)
        res = res.fetchall() if sql_statement.lower().startswith("select") else None
        con.commit()
    return res


def executemany_sql_statement(sql_statement: str, arguments: List[Tuple[str]]) -> Any:
    """Exécuter plusieurs fois la même commande SQL pour les différents arguments.

    :param sql_statement: La commande SQL.
    :type sql_statement: str
    :param arguments: La liste d'arguments à utiliser adapter la commande SQL.
    :type arguments: List[Tuple[str]]
    :return: Le résultat de la commande SQL.
    :rtype: Any
    """
    with closing(sqlite3.connect(DB_FILEPATH)) as con:
        cur = con.cursor()
        res = cur.executemany(sql_statement, arguments)
        con.commit()
    return res


def populate_database_from_dataframe(
    table_name: str, df: pd.DataFrame, if_exists: str = "append", index: bool = False
) -> None:
    """Insérer dans une table les données d'un DataFrame.

    :param table_name: Nom de la table à populer.
    :type table_name: str
    :param df: DataFrame à utiliser comme source de données.
    :type df: pd.DataFrame
    :param if_exists: Comportement à adopter si la table existe. Plusieurs options
        possibles:

        - fail: retourne une erreur.
        - replace: "Drop" la table avant l'insertion des nouvelles valeurs.
        - append: Insertion des valeurs dans la table.
    :type if_exists: str, optional
    :param index: Inclure les index du DataFrame comme colonne dans la table. Ceux-ci
        sont omis par défaut.
    :type index: bool, optional
    """
    with closing(sqlite3.connect(DB_FILEPATH)) as con:
        df.to_sql(name=table_name, con=con, if_exists=if_exists, index=index)
        con.commit()


def get_data(table_name: str, attributes: List[str]) -> List[Dict[str, str]]:
    """Obtenir les données d'une table en filtrant les attributs retournés.

    :param table_name: Nom de la table sur laquelle faire la requête.
    :type table_name: str
    :param attributes: Attributs à sélectionner.
    :type attributes: List[str]
    :return: Résultats de la requête. Chaque élément de la liste est une ligne de la
        table, et chacun de ceux-ci est représenté sous la forme d'un dictionnaire.
    :rtype: List[Dict[str, str]]
    """
    with closing(sqlite3.connect(DB_FILEPATH)) as con:
        cur = con.cursor()
        data = []
        for row in cur.execute(f"SELECT {','.join(attributes)} FROM {table_name}"):
            data.append(dict(zip(attributes, row)))
        return data
