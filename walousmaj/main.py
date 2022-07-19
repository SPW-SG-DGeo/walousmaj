"""WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>."""
from typing import Any, Dict

from walousmaj import LOG_FILEPATH
from walousmaj.core import Pipeline
from walousmaj.core.stages import (
    Coalescence,
    Comparison,
    Compression,
    Compulsion,
    Cropping,
    Erosion,
    Fusion,
    Inference,
    Initialization,
    Preprocessing,
    Reprojection,
    Resampling,
    Vectorization,
)
from walousmaj.utils import log

Config = Dict[str, Any]


def main(config: Config = None, resume: bool = False):
    config = {} if not config else config
    if not resume:
        config["resume"] = resume
    steps = [
        Initialization,
        Preprocessing,
        Inference,
        Resampling,
        Erosion,
        Fusion,
        Compulsion,
        Comparison,
        Coalescence,
        Cropping,
        Reprojection,
        Compression,
        Vectorization,
    ]
    logger = log.get_logger(LOG_FILEPATH)
    pipe = Pipeline(steps, config, resume, logger)
    pipe()
