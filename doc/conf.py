"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Fichier de configuration pour la documentation Sphinx.
"""
import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath("../walousmaj/"))


# -- Information sur le projet ------------------------------------------------

project = "WalousMàJ"
copyright = "2021, MIT"
author = "Aerospacelab"

release = "1.0.0"


# -- Configuration générale ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.apidoc",
    "m2r2",
]

source_suffix = [".rst", ".md"]

# Pour éviter de trier les fonctions par ordre alphabétique
autodoc_member_order = "bysource"

# Pour rajouter les class __init__ dans la documentation
autoclass_content = "both"

# Pour rajouter tous les paths qui contiennent un template
templates_path = ["_templates"]

# Pour exclure des fichiers
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "api/static", "api/templates"]


# -- Options pour l'output HTML ---------------------------------------------

# Sélection du thème
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]


# -- Readthedocs -------------------------------------------------------------

master_doc = "index"
apidoc_module_dir = "../walousmaj/"
apidoc_output_dir = "./source"
apidoc_separate_modules = True
apidoc_extra_args = ["-f"]
