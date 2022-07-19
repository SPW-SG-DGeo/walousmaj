"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour les encodages et décodages de classes OCS.
"""
from functools import lru_cache
from typing import Dict, List, Union

import numpy as np
from numpy import ma


OCS_TITLES = {
    1: "Revêtement artificiel au sol",
    2: "Constructions artificielles hors sol",
    3: "Réseau ferroviaire",
    4: "Sols nus",
    5: "Eaux de surface",
    6: "Couvert herbacé en rotation",
    7: "Couvert herbacé toute l'année",
    8: "Résineux (> 3m)",
    9: "Feuillus (> 3m)",
    11: "Revêtement artificiel au sol (pont)",
    15: "Revêtement artificiel au sol (sous eau)",
    18: "Revêtement artificiel au sol (sous résineux)",
    19: "Revêtement artificiel au sol (sous feuillus)",
    28: "Constr. artificielles hors sol (sous résineux)",
    29: "Constr. artificielles hors sol (sous feuillus)",
    31: "Pont au dessus du réseau ferroviaire",
    38: "Réseau ferroviaire (sous résineux)",
    39: "Réseau ferroviaire (sous feuillus)",
    51: "Ponts sur l'eau",
    55: "Eaux de surface (2 niveaux)",
    58: "Eaux de surface (sous résineux)",
    59: "Eaux de surface (sous feuillus)",
    62: "Serres",
    71: "Couvert herbacé toute l'année (sous pont)",
    73: "Couvert herbacé toute l'année (sous réseau ferroviaire)",
    75: "Couvert herbacé toute l'année (sous pont-canal)",
    80: "Résineux (≤ 3m)",
    81: "Résineux (sous pont)",
    83: "Résineux (sous réseau ferroviaire)",
    85: "Résineux (sous pont - canal)",
    90: "Feuillus (≤ 3m)",
    91: "Feuillus (sous pont)",
    93: "Feuillus (sous réseau ferroviaire)",
    95: "Feuillus (sous pont - canal)",
}

OCS_TO_MODELS_LABELS = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
    7: 6,
    8: 7,
    9: 8,
    80: 9,
    90: 10,
}


@lru_cache()
def models_to_ocs_labels() -> Dict[int, int]:
    """Decodage des labels du modèle vers les labels WalOUS_OCS.

    :return: Un dictionnaire avec les pairs clé[modèle label] - valeur[ocs label].
    :rtype: Dict[int, int]
    """
    return {v: k for k, v in OCS_TO_MODELS_LABELS.items()}


@lru_cache()
def ocs_double_to_main_labels(nodata: int = None) -> Dict[int, int]:
    """Encodage des labels WalOUS_OCS en labels principaux WalOUS_OCS.

    :return: Un dictionnaire avec les pairs clé[ocs label] - valeur[ocs label principal]
    :rtype: Dict[int, int]
    """
    encoding = {
        k: k if k in OCS_TO_MODELS_LABELS else (k // 10) for k in OCS_TITLES.keys()
    }
    if nodata is not None:
        if nodata in encoding:
            raise ValueError(
                f"La valeur pour `nodata` {nodata} fait déjà partie de clé d'encodage."
            )
        encoding[nodata] = nodata
    return encoding


def ocs_double_to_main_labels_divmod(
    array: Union[np.ndarray, ma.MaskedArray], nodata: int = None
) -> Union[np.ndarray, ma.MaskedArray]:
    """Encodage des labels WalOUS_OCS en labels principaux WalOUS_OCS.

    :return: Un dictionnaire avec les pairs clé[ocs label] - valeur[ocs label principal]
    :rtype: Dict[int, int]
    """
    reject_list = list(OCS_TO_MODELS_LABELS.keys())
    if nodata is not None:
        reject_list.append(nodata)
    div, mod = np.divmod(array, np.where(np.isin(array, reject_list), 1, 10))
    return ma.where(mod, mod, div)


def to_mapping_array(mapping_dict: Dict[int, Union[int, List[int]]]) -> np.ndarray:
    """Convertir un dictionnaire d'encodages/décodages en un array d'encodages
    décodages.

    Ceci permet de réduire grandement le temps nécessaire pour faire l'encodage/
    décodage. Ceci est par exemple utilisé pour décoder les labels de sortie du modèle
    d'inférence en labels WalOUS_OCS.

    :param mapping_dict: Dictionnaire d'encodages/décodages
    :type mapping_dict: Dict[int, Union[int, List[int]]]
    :return: Array d'encodages/décodages
    :rtype: np.ndarray
    """
    k = np.array(list(mapping_dict.keys()))
    v = np.array(list(mapping_dict.values()))
    if v.ndim > 1:
        map_array_shape = (k.max() + 1, v.shape[1])
    else:
        map_array_shape = k.max() + 1
    mapping_array = np.zeros(map_array_shape, dtype="uint8")
    mapping_array[k] = v
    return mapping_array
