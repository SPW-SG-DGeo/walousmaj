"""WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>."""
from pathlib import Path

import setuptools

long_description = Path("README.md").read_text(encoding="utf-8")

setuptools.setup(
    name="walousmaj",
    version="1.0.0",
    author="Aerospacelab",
    description="Mise à jour de la carte d'occupation des sols de Wallonie.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.tesseract.ai",
    packages=setuptools.find_packages(),
    package_data={
        "walousmaj": [
            "api/templates/*",
            "assets/aoi/*",
            "assets/config/*",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
