"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'Enums pour les différents stages, status, et formats.
"""
from enum import Enum, IntEnum, auto


class AutoIncrement(IntEnum):
    def _generate_next_value_(name, start, count, last_values):
        return count


class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


class StageOrder(AutoIncrement):
    RESTART = auto()
    INITIALIZATION = auto()
    PREPROCESSING = auto()
    INFERENCE = auto()
    RESAMPLING = auto()
    EROSION = auto()
    FUSION = auto()
    COMPULSION = auto()
    COMPARISON = auto()
    COALESCENCE = auto()
    CROPPING = auto()
    REPROJECTION = auto()
    COMPRESSION = auto()
    VECTORIZATION = auto()


class Status(Enum):
    ERROR = auto()
    PENDING = auto()
    ONGOING = auto()
    DONE = auto()
    SKIPPED = auto()


class StageOutputType(Enum):
    DIRECTORY = auto()
    FILE = auto()


class ComparisonOutputFormatEnum(IntEnum):
    BINARY_MASK = 0
    BEFORE_AFTER_2B = 1
    BEFORE_AFTER_SINGLE = 2


class CompressionMethodEnum(AutoName):
    LZW = auto()
    DEFLATE = auto()
    PACKBITS = auto()


class VectorizationConnectednessEnum(IntEnum):
    C4 = 4
    C8 = 8
