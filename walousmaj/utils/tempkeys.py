"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Utilitaires liés aux Templates.
"""
from string import Template
from typing import List


def get_template_keys(t: Template) -> List[str]:
    """Obtenir les clés (placeholders) d'un Template.

    Les clés sont les éléments à substituer dans un Template. Ils sont identifiables
    grâce aux délimiteurs `$`.

    :param t: Template pour lequel il faut extraire les clés
    :type t: Template
    :return: Liste de clés
    :rtype: List[str]
    """
    return [k[1] or k[2] for k in Template.pattern.findall(t.template) if k[1] or k[2]]
