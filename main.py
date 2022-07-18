"""WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>."""
import argparse
from collections import defaultdict
from pathlib import Path

from yaml import Loader, load

from walousmaj.main import main

if __name__ == "__main__":
    # Traitement des paramètres pour les lignes de commandes
    parser = argparse.ArgumentParser(
        description="Mise à jour de la carte d'occupation du sol du territoire wallon",
    )
    parser.add_argument(
        "-cf",
        "--config_filepath",
        help="chemin vers le fichier de configuration",
        type=str,
    )
    parser.add_argument(
        "-r",
        "--resume",
        help="reprendre la dernière exécution",
        action="store_true",
    )
    args = parser.parse_args()

    if not args.resume and not args.config_filepath:
        parser.error("-r and -cf can't be both omitted.")

    # Lecture du fichier de configuration, si applicable
    if args.config_filepath:
        config = load(Path(args.config_filepath).read_bytes(), Loader=Loader)
    else:
        config = defaultdict(dict)

    main(config, resume=args.resume)
