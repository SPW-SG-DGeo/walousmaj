"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour la génération de paths.
"""
from pathlib import Path
from string import Template
from typing import List

from walousmaj.utils.typing import Maille


def get_filepath(
    dir: str,
    folder_structure: Template,
    maille: Maille,
    mkdir: bool = True,
) -> Path:
    """Obtenir le path vers le fichier d'une maille.

    :param dir: Dossier racine duquel découle `folder_structure`.
    :type dir: str
    :param folder_structure: Structure du dossier racine. Les éventuelles variables
        seront substituées par les données de la `maille`.
    :type folder_structure: Template
    :param maille: Objet décrivant la maille et contenant les substitus pour les
        éventuelles variables du Template `folder_structure`.
    :type maille: Maille
    :param mkdir: Option pour créer ou non les dossiers parents. True par défaut.
    :type mkdir: bool, optional
    :return: Path pointant sur le fichier correspondant à la maille.
    :rtype: Path
    """
    filepath = Path(dir) / folder_structure.substitute(maille)
    if mkdir:
        filepath.parent.mkdir(parents=True, exist_ok=True)

    return filepath


def parse_input_queue(raw_db_input_queue: str) -> List[Path]:
    """Extraction et conversion des paths de l'input_queue de la table `job`.

    :param raw_db_input_queue: String sauvée dans la table `job` pour l'attribut
        `input_queue` d'un job.
    :type raw_db_input_queue: str
    :return: Une liste de Path représentant l'input_queue
    :rtype: List[Path]
    """
    if not raw_db_input_queue or raw_db_input_queue == "[]":
        return []
    iq = raw_db_input_queue.lstrip("['").rstrip("']")
    return [Path(x) for x in iq.split("', '")]
