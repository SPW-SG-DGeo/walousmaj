"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour valider le fichier de configuration.
"""
from pathlib import Path
from string import Template
from typing import Dict, List

import geopandas as gpd
import pyproj
import rasterio as rio
from detectron2.config import get_cfg
from detectron2.projects.deeplab import add_deeplab_config
from pydantic import (
    BaseModel,
    Field,
    PositiveFloat,
    PositiveInt,
    StrictBool,
    StrictStr,
    validator,
)

from walousmaj import DEFAULT_MODEL_CONFIG_FILEPATH, WALLONIA_AOI_FILEPATH
from walousmaj.utils.enums import (
    ComparisonOutputFormatEnum,
    CompressionMethodEnum,
    VectorizationConnectednessEnum,
)


class ExtensionStr(StrictStr):
    """Validation d'une extension. La délimitation de l'extension n'est pas obligatoire."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def validate(cls, v):
        return v if v.startswith(".") else "." + v


class TemplateStr(StrictStr):
    """Validation d'un `Template` de la librairie `string`."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def validate(cls, v):
        if isinstance(v, Template):
            return v
        return Template(v)


class FilePath(StrictStr):
    """Validation du path vers un fichier. Ce fichier doit exister."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def validate(cls, v):
        if isinstance(v, Path):
            return cls(str(v))
        if not isinstance(v, str):
            raise TypeError("string required")
        path = Path(v)
        if not path.is_file():
            raise ValueError("file doesn't exist")

        return v


class DirectoryPath(StrictStr):
    """Validation du path vers un dossier. Ce dossier doit exister."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")
        path = Path(v)
        if not path.is_dir():
            raise ValueError("folder doesn't exist")
        return v


class GeoFilePath(FilePath):
    """Validation d'une donnée vectorielle."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            details="Path vers une donnée vectorielle au format Shapefile ou GeoJSON",
            examples=[
                "/path/to/file.shp",
                "/path/to/file.geojson",
            ],
        )

    @classmethod
    def validate(cls, v):
        if not v.endswith((".shp", ".geojson")):
            raise ValueError("unsupported format: expected a Shapefile or a GeoJSON")
        gdf = gpd.read_file(v)
        if not gdf.crs:
            raise ValueError("no projection (CRS) found")
        if gdf.shape[0] == 0:
            raise ValueError("no geometries found")
        return v


class TIFFilePath(FilePath):
    """Validation d'une donnée raster."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            details="Path vers un raster au format TIF(F)",
            examples=[
                "/path/to/file.tif",
                "/path/to/file.tiff",
            ],
        )

    @classmethod
    def validate(cls, v):
        if not v.endswith((".tif", ".tiff")):
            raise ValueError("unsupported format: expected a raster (TIF(F))")
        with rio.open(v) as raster:
            if not raster.crs:
                raise ValueError("no projection (CRS) found")
        return v


class ModelConfigFilePath(FilePath):
    """Validation d'un fichier de configuration d'un modèle Detectron2."""

    @classmethod
    def __get_validators__(cls):
        for x in [super().validate, cls.validate]:
            yield x

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            details="Path vers un fichier de configuration Detectron2 au format YAML",
            examples=[
                "/home/walous/model_config.yaml",
                "/home/walous/model_config.yml",
            ],
        )

    @classmethod
    def validate(cls, v):
        if not v.endswith((".yaml", ".yml")):
            raise ValueError("unsupported format: expected a YAML)")
        try:
            cfg = get_cfg()
            add_deeplab_config(cfg)
            cfg.merge_from_file(v)
            assert Path(
                cfg.MODEL.WEIGHTS
            ).is_file(), f"file containing model's weights couldn't be found: {cfg.MODEL.WEIGHTS}"
        except (Exception, AssertionError) as e:
            raise ValueError(e)  # Converti en ValueError pour parsing par Pydantic

        return v


class CRSType(str):
    """Validation d'un système de référence de coordonnées."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            details="Une description du CRS. Supporte EPSG Projected, Geographic or Compound CRS, une definition well known text (WKT) CRS, une déclaration PROJ.4",
            examples=[
                "EPSG:31370",
                "'+proj=lcc +lat_1=51.16666723333333 +lat_2=49.8333339 +lat_0=90 +lon_0=4.367486666666666 +x_0=150000.013 +y_0=5400088.438 +ellps=intl +towgs84=-106.869,52.2978,-103.724,0.3366,-0.457,1.8422,-1.2747 +units=m +no_defs'",
            ],
        )

    @classmethod
    def validate(cls, v):
        try:
            pyproj.CRS.from_user_input(v)
        except pyproj.exceptions.CRSError as e:
            raise ValueError(e)
        return v


class InitializationValidator(BaseModel):
    maillage_filepath: GeoFilePath = Field(
        ...,
        description="Fichier contenant le maillage des orthophotos",
    )
    mailles: List[str] = Field(
        [],
        description="Liste de mailles (IMAGE_NAME) à considérer",
        examples=[
            [
                "ORTHO_2018__00800021",
                "ORTHO_2018__00810021",
            ],
            [
                "ORTHO_2018__00800021",
            ],
        ],
    )
    aoi_filepath: GeoFilePath = Field(
        None,
        description="Fichier contenant une AOI pour filtrer les mailles d'intérêt. Peut être utilisé en conjonction avec l'argument `mailles`",
    )

    class Config:
        extra = "forbid"


class PreprocessingValidator(BaseModel):
    ortho_directory: DirectoryPath = Field(
        ...,
        description="Dossier racine des orthophotos. La structure de ce dossier est renseignée via `folder_structure`",
    )
    mns_filepath: TIFFilePath = Field(
        ...,
        description="Fichier contenant le Modele Numerique de Surface dérivé, par photogrammetrie, des orthophotos",
    )
    mnt_filepath: TIFFilePath = Field(
        ...,
        description="Fichier contenant le Modele Numerique de Terrain",
    )

    class Config:
        extra = "forbid"


class InferenceValidator(BaseModel):
    model_config_filepath: ModelConfigFilePath = Field(
        None,
        description="Fichier de configuration du model d'inférence. Si `null` alors le fichier de configuration par default est utilisé",
    )
    overlap: PositiveInt = Field(
        12,
        description="Chevauchement entre les vignettes adjacentes contenant les données d'entrée. Doit être divisible par 2",
    )
    output_nodata: PositiveInt = Field(
        255,
        description="Valeur à attribuer aux pixels pour lesquels il n'y a pas de données",
    )

    @validator("overlap", always=True)
    def divisible_by_2(cls, overlap, values):
        if overlap % 2 != 0:
            raise ValueError("must by divisible by 2")
        else:
            return overlap

    @validator("model_config_filepath", always=True)
    def set_model_config_filepath(cls, v, values, **kwargs):
        return v or Path(DEFAULT_MODEL_CONFIG_FILEPATH)

    class Config:
        extra = "forbid"
        validate_assignment = True


class ResamplingValidator(BaseModel):
    skip: StrictBool = Field(
        False,
        description="Option pour sauter l'étape.",
    )
    upscale_factor_x: PositiveFloat = Field(
        None,
        description="Facteur d'agrandissement sur l'axe X pour le rééchantillonnage. Si `null` alors ce facteur sera déterminé automatiquement pour obtenir une résolution spatiale de 1m/pixel",
    )
    upscale_factor_y: PositiveFloat = Field(
        None,
        description="Facteur d'agrandissement sur l'axe Y pour le rééchantillonnage. Si `null` alors ce facteur sera déterminé automatiquement pour obtenir une résolution spatiale de 1m/pixel",
    )

    class Config:
        extra = "forbid"


class ErosionValidator(BaseModel):
    skip: StrictBool = Field(
        False,
        description="Option pour sauter l'etape.",
    )
    threshold: PositiveInt = Field(
        16,
        description="Seuil du nombre de pixels connectés en dessous duquel une zone sera fusionnée à la zone voisine la plus large. Taille minimum, en pixels des polygones à garder.",
    )
    connectedness: VectorizationConnectednessEnum = Field(
        VectorizationConnectednessEnum.C8.value,
        description="Directions à utiliser pour considérer des pixels connectés appartenant à la même zone. 4: Nord, Sud, Ouest, et Est ou 8: NSOE + diagonales.",
    )

    class Config:
        extra = "forbid"


class FusionSourcePropertiesValidator(BaseModel):
    shapes_filepath: GeoFilePath = Field(
        ...,
        description="Fichier contenant les geometries d'une classe principale à considerer pour la fusion de double labels",
    )
    buffer: float = Field(
        0,
        description="Tampon à appliquer à chaque géometrie afin de l'éroder ou de la dilater. Les unités depdendent du CRS des géometries de `shapes_filepath`",
    )
    filter_on_labels: List[PositiveInt] = Field(
        ...,
        description="Classes principales 'vue du ciel' sur lesquelles la fusion du double label doit être considerée",
    )
    main_label: PositiveInt = Field(
        ...,
        description="Valeur de la classe secondaire pour toutes les géometries de `shapes_filepath`",
    )

    class Config:
        extra = "forbid"


class FusionValidator(BaseModel):
    skip: StrictBool = Field(
        True,
        description="Option pour sauter l'étape.",
    )
    sources: Dict[str, FusionSourcePropertiesValidator] = Field(
        {},
        description="Liste de sources pour la constitution des doubles labels",
    )

    @validator("sources", always=True)
    def check_no_skip_args(cls, v, values, **kwargs):
        if not v and not values["skip"]:
            raise ValueError("`sources` can't be empty if `skip` is set to False")
        return v

    class Config:
        extra = "forbid"


class CompulsionValidator(BaseModel):
    skip: StrictBool = Field(
        True,
        description="Option pour sauter l'étape",
    )
    shapes_filepath: GeoFilePath = Field(
        None,
        description="Fichier contenant les géometries à forcer sur la donnée",
    )
    default_label: PositiveInt = Field(
        None,
        description="Classe (principale ou double label) à associer à chaque géometrie de `shapes_filepath`. Si `null` alors la classe sera extraite du `shapes_filepath` via le champs `value`, ainsi chaque géometrie peut être associée à une classe différente",
    )

    @validator("shapes_filepath", always=True)
    def check_no_skip_args(cls, v, values, **kwargs):
        if not v and not values["skip"]:
            raise ValueError(
                "`shapes_filepath` can't be empty if `skip` is set to False"
            )
        return v

    @validator("default_label", always=True)
    def check_no_skip_no_default_label(cls, v, values, **kwargs):
        if not v and values["shapes_filepath"] and not values["skip"]:
            gdf = gpd.read_file(values["shapes_filepath"])
            if "value" not in gdf.columns:
                raise ValueError(
                    "`default_label` is empty and `shapes_filepath` doesn't contain a `value` attribute"
                )
        return v

    class Config:
        extra = "forbid"


class ComparisonValidator(BaseModel):
    skip: StrictBool = Field(
        True,
        description="Option pour sauter l'étape",
    )
    previous_ocs_filepath: TIFFilePath = Field(
        None,
        description="Fichier d'occupation du sol utilisé comme référence pour la comparaison",
    )
    only_main_label: StrictBool = Field(
        True,
        description="Option pour ne considerer que les classes principales pour la comparaison. Ainsi une difference au niveau du second label ne sera pas considérée comme un changement si la classe principale est la meme",
    )
    output_format: ComparisonOutputFormatEnum = Field(
        ComparisonOutputFormatEnum.BINARY_MASK,
        description="Format des données de sortie de l'étape de comparaison. Masque binaire, double couche 'avant-apres', couche unique '(avant*1000)+après'",
    )

    @validator("previous_ocs_filepath", always=True)
    def check_no_skip_args(cls, v, values, **kwargs):
        if not v and not values["skip"]:
            raise ValueError(
                "`previous_ocs_filepath` can't be empty if `skip` is set to False"
            )
        return v

    class Config:
        extra = "forbid"
        use_enum_values = True


class CroppingValidator(BaseModel):
    skip: StrictBool = Field(
        False,
        description="Option pour sauter l'étape.",
    )
    aoi_filepath: GeoFilePath = Field(
        WALLONIA_AOI_FILEPATH,
        description="Fichier contenant l'AOI. Les zones du raster non contenue dans cette AOI seront rognées",
    )
    all_touched: StrictBool = Field(
        True,
        description="Option pour considérer tous les pixels touchés par l'AOI",
    )

    class Config:
        extra = "forbid"


class ReprojectionValidator(BaseModel):
    skip: StrictBool = Field(
        False,
        description="Option pour sauter l'étape.",
    )
    to_srs: CRSType = Field(
        "EPSG:3812",
        description="Système de reference spatiale dans lequel doit être reprojeté la donnee. En utilisant cette option, GDAL determinera automatiquement les etapes de transformation pour la reprojection. Ceci peut mener à une reprojection sous-optimale",
    )
    coordinate_transform: StrictStr = Field(
        "+proj=pipeline +step +inv +proj=lcc +lat_0=90 +lon_0=4.36748666666667 +lat_1=51.1666672333333 +lat_2=49.8333339 +x_0=150000.013 +y_0=5400088.438 +ellps=intl +step +proj=hgridshift +grids=bd72lb72_etrs89lb08.gsb +step +proj=lcc +lat_0=50.797815 +lon_0=4.35921583333333 +lat_1=49.8333333333333 +lat_2=51.1666666666667 +x_0=649328 +y_0=665262 +ellps=GRS80",
        description="Etapes de transformation pour la projection. Celles-ci seront utilisées par GDAL a la place de celles prevues par défaut. Les donnees sources seront dans le meme référentiel que les orthophotos",
    )
    target_extents: StrictStr = Field(
        "540000.000 520000.000 800000.000 670000.000",
        description="Extensions du raster de sortie: xmin ymin xmax ymax",
    )
    target_resolution: StrictStr = Field(
        "1 1",
        description="Résolution du raster de sortie: xres yres",
    )
    target_aligned_pixels: StrictBool = Field(
        True,
        description="Option pour aligner les pixels aux extensions et résolution du raster de sortie.",
    )

    @validator("coordinate_transform", always=True)
    def check_no_skip_args(cls, v, values, **kwargs):
        if not v and not values["to_srs"] and not values["skip"]:
            raise ValueError(
                "`to_srs` and `coordinate_transform` can't both be null if `skip` is set to False"
            )
        return v

    @validator("target_extents", always=True)
    def check_target_extents(cls, v, values, **kwargs):
        if v:
            if len(v.split(" ")) != 4:
                raise ValueError(
                    "`target_extents` must have the following format: xmin ymin xmax ymax"
                )
            try:
                list(map(float, v.split(" ")))
            except ValueError:
                raise ValueError(
                    "`target_extents` must contain floats with the following format: xmin ymin xmax ymax"
                )
        return v

    @validator("target_resolution", always=True)
    def check_target_resolution(cls, v, values, **kwargs):
        if v:
            if len(v.split(" ")) != 2:
                raise ValueError(
                    "`target_resolution` must have the following format: xres yres"
                )
            try:
                list(map(float, v.split(" ")))
            except ValueError:
                raise ValueError(
                    "`target_resolution` must contain floats with the following format: xres yres"
                )
        return v

    @validator("target_aligned_pixels", always=True)
    def check_target_aligned_pixels_args(cls, v, values, **kwargs):
        if v and not values["target_resolution"] and not values["target_extents"]:
            raise ValueError(
                "`target_resolution` and `target_extents` can't both be null if `target_aligned_pixels` is set to True"
            )
        return v

    class Config:
        extra = "forbid"


class CompressionValidator(BaseModel):
    skip: StrictBool = Field(
        False,
        description="Option pour sauter l'étape",
    )
    method: CompressionMethodEnum = Field(
        CompressionMethodEnum.LZW,
        description="Methode de compression à utiliser",
    )

    class Config:
        extra = "forbid"


class VectorizationValidator(BaseModel):
    skip: StrictBool = Field(
        False,
        description="Option pour sauter l'étape",
    )
    connectedness: VectorizationConnectednessEnum = Field(
        VectorizationConnectednessEnum.C8.value,
        description="Directions à utiliser pour considérer des pixels connectés appartenant à la même zone. 4: Nord, Sud, Ouest, et Est ou 8: NSOE + diagonales.",
    )
    output_format: StrictStr = Field(
        "GPKG", description="Format de la donnée de sortie."
    )
    output_file_extension: ExtensionStr = Field(
        ".gpkg", description="Extension à utiliser pour la donnée de sortie."
    )

    class Config:
        extra = "forbid"
        use_enum_values = True


class ConfigValidator(BaseModel):
    folder_structure: TemplateStr = Field(
        ...,
        description="Structure du dossier des orthophotos",
        details="Les éventuelles variables doivent suivre la convention suivante: ${variable}. La variable doit être renseignée comme attribut dans le maillage",
        examples=[
            "planche_${MAPSHEET}/${IMAGE_NAME}.tif",
            "${IMAGE_NAME}.tif",
        ],
    )
    workspace_directory: StrictStr = Field(
        ...,
        description="Dossier dans lequel les fichiers temporaires seront sauvés",
        details="Les privilèges de lecture et d'écriture sur le dossier parent sont requis. Un espace de 5T est nécessaire",
    )
    output_directory: StrictStr = Field(
        ...,
        description="Dossier dans lequel les données de sortie seront sauvées",
        details="Le privilège d'écriture sur le dossier parent est requis. Un espace de 25G est nécessaire",
    )
    output_filename: StrictStr = Field(
        ...,
        description="Prefix à attribuer aux noms des fichiers des données de sortie",
        details="Ce prefix ne doit pas inclure l'extension du fichier",
    )
    initialization: InitializationValidator = Field(
        ...,
        description="Paramètres pour l'étape d'initilialisation",
        details="Cette étape s'assure de la validité des arguments pour la solution et prépare les différents outils nécessaires à son execution",
    )
    preprocessing: PreprocessingValidator = Field(
        default_factory=PreprocessingValidator,
        description="Paramètres pour l'étape de preprocessing",
        details="Cette étape prépare les données d'entrée du modèle d'inference",
    )
    inference: InferenceValidator = Field(
        default_factory=InferenceValidator,
        description="Paramètres pour l'étape d'inférence",
        details="Dans cette étape, le modèle de segmentation fait ses predictions et celles sont consolidées par maille",
    )
    resampling: ResamplingValidator = Field(
        default_factory=ResamplingValidator,
        description="Paramètres pour l'étape de rééchantillonnage",
        details="Dans cette étape optionnelle, les prédictions du modèle sont rééchantillonnées à la résolution spatiale souhaitée (par défaut 1m/pixel)",
    )
    erosion: ErosionValidator = Field(
        default_factory=ErosionValidator,
        description="Paramètres pour l'étape d'érosion",
        details="Dans cette étape optionnelle, les petites zones de quelques pixels sont fusionnées avec leur voisin le plus large afin de proposer une unite minimale de cartographie. Elle repose en partie sur `gdal_sieve`. Pour plus d'information: https://gdal.org/programs/gdal_sieve.html",
    )
    fusion: FusionValidator = Field(
        default_factory=FusionValidator,
        description="Paramètres pour l'étape de fusion",
        details="Cette étape optionnelle intègre les double labels en considérant différentes sources externes de donnees vectorielles",
    )
    compulsion: CompulsionValidator = Field(
        default_factory=CompulsionValidator,
        description="Paramètres pour l'etape de forçage",
        details="Cette étape optionnelle force des géométries sur la donnée de sortie. Cette etape peut être utilisée afin de corriger certaines erreurs de prédictions",
    )
    comparison: ComparisonValidator = Field(
        default_factory=ComparisonValidator,
        description="Paramètres pour l'étape de comparaison",
        details="Dans cette étape optionnelle, la donnée de sortie est comparée à une donnée de référence afin d'extraire les différences",
    )
    cropping: CroppingValidator = Field(
        default_factory=CroppingValidator,
        description="Paramètres pour l'étape de rognage",
        details="Cette étape optionnelle rogne les données sur une AOI (le territoire wallon par défaut). Elle repose en partie sur `gdal_rasterize`. Pour plus d'information: https://gdal.org/programs/gdal_rasterize.html",
    )
    reprojection: ReprojectionValidator = Field(
        default_factory=ReprojectionValidator,
        description="Paramètres pour l'étape de reprojection.",
        details="Cette étape optionnelle reprojette les données dans le référentiel souhaitée. Elle repose en partie sur `gdalwarp`. Pour plus d'information: https://gdal.org/programs/gdalwarp.html",
    )
    compression: CompressionValidator = Field(
        default_factory=CompressionValidator,
        description="Paramètres pour l'étape de compression",
        details="Cette étape optionnelle compresse les données pour réduire leurs tailles. Elle repose en partie sur `gdal_translate`. Pour plus d'information: https://gdal.org/programs/gdal_translate.html",
    )
    vectorization: VectorizationValidator = Field(
        default_factory=VectorizationValidator,
        description="Paramètres pour l'étape de vectorisation",
        details="Cette étape optionnelle vectorise les données. Attention cette étape peut prendre beaucoup de temps. Elle repose en partie sur `gdal_polygonize.py`. Pour plus d'information: https://gdal.org/programs/gdal_polygonize.html",
    )

    class Config:
        extra = "allow"
