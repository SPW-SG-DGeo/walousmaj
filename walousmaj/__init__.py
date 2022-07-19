from pathlib import Path

from yaml import Loader, load

default_variables = load(
    (
        Path(__file__).resolve().parent / "assets/config/default_variables.yml"
    ).read_bytes(),
    Loader=Loader,
)

LOG_FILEPATH = default_variables["log_relative_filepath"]
DB_FILEPATH = default_variables["database_relative_filepath"]
CONFIG_DEFAULT_FILEPATH = str(
    Path(__file__).resolve().parent
    / default_variables["default_config_relative_filepath"]
)
WALLONIA_AOI_FILEPATH = str(
    Path(__file__).resolve().parent
    / default_variables["wallonia_aoi_relative_filepath"]
)
DEFAULT_MODEL_CONFIG_FILEPATH = str(
    Path(__file__).resolve().parent
    / default_variables["default_model_config_relative_filepath"]
)
