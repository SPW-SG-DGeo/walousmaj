"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Utilitaire gérant les permissions des fichiers/dossiers créés.
"""
import shlex
from subprocess import check_call


def update_permissions(directory: str) -> None:
    """Mise à jour des permissions du dossier donné, ainsi que tous les dossiers et
    fichiers inclus dedans.

    En octal, les permissions 775 sont données aux dossiers. Pour les fichiers, 664.

    :param directory: Chemin du dossier où appliquer le changement de permissions
    :type directory: str
    """
    check_call(shlex.split(f"find {directory} -type d -exec chmod 775 {{}} ;"))
    check_call(shlex.split(f"find {directory} -type f -exec chmod 664 {{}} ;"))
