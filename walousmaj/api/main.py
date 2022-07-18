"""WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>."""
import io
import json
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from walousmaj import CONFIG_DEFAULT_FILEPATH, LOG_FILEPATH
from walousmaj.api.schemas import Maille
from walousmaj.database.crud import get_data
from walousmaj.database.job import get_last_job
from walousmaj.database.maille import TABLE_NAME as MAILLE_TABLE_NAME
from walousmaj.database.stage import TABLE_NAME as STAGE_TABLE_NAME
from walousmaj.utils.enums import Status
from walousmaj.utils.validators import ConfigValidator

TEMPLATE_MAILLE_TABLE_PATH = "maille_table.html"
TEMPLATE_STAGE_TABLE_PATH = "stage_table.html"


tags_metadata = [
    {
        "name": "Launch",
        "description": "Executer la solution.",
    },
    {
        "name": "Resume",
        "description": "Reprendre l'execution.",
    },
    {
        "name": "Config",
        "description": "Obtenir le fichier de configuration.",
    },
    {
        "name": "Documentation Config",
        "description": "Obtenir la documentation sur le fichier de configuration.",
    },
    {
        "name": "Log",
        "description": "Obtenir le fichier de log.",
    },
    {
        "name": "Status",
        "description": "Obtenir le status global.",
    },
    {
        "name": "Détails",
        "description": "Obtenir le details du status par maille.",
    },
    {
        "name": "Détails Table",
        "description": "Obtenir le details du status par maille sous forme de table interactive.",
    },
    {
        "name": "Détails Export",
        "description": "Télécharger le details du status par maille sous forme de CSV.",
    },
]

description = """
WalOUSMàJ API permet la mise à jour de la carte d'occupation du sol de Wallonie.

Elle s'inscrit dans le cadre du marché, établi en 2021 entre le [SPW](https://spw.wallonie.be/) et [Aerospacelab](https://www.aerospacelab.be/), de mise à jour de la carte d'occupation du sol de Wallonie.

## Exécution

Afin de générer la nouvelle carte d'occupation du sol, un fichier de configuration doit être soumis à `/launch`. La description des champs de ce fichier de configuration est disponible via `/config_doc` ou, de manière interactive via `/redoc`. Ce fichier configurera l'exécution selon vos attentes. Par exemple, il vous est possible via ce fichier de choisir le format de la carte des changements, ou encore de choisir les mailles sur lesquelles vous voulez prendre en compte.

## Suivi

Une fois l'exécution lancée via `/launch`, vous pouvez suivre sa progression via:
- `/status`: pour obtenir le status global par étape
- `/details_table`: pour voir le status par maille

## Export

Il vous est également possible d'exporter quelques données dans un fichier lors de l'exécution:
- les logs via `/log`
- les détails par maille via `/details_export`

De plus, la documentation sur le fichier de configuration peut être exportée via `/config_doc`. Afin d'obtenir la configuration de l'exécution en cours, `/config` peut être utilisé. Cependant, si aucune exécution n'est en cours, le fichier de configuration par défaut sera renvoyé.

## Reprise

Si l'exécution s'est interrompue suite à une cause externe, il vous est possible de reprendre l'exécution là où elle s'est interrompue via `/resume`. Aucun fichier de configuration n'est nécessaire dans ce cas puisque la configuration de l'exécution précédente sera utilisée.

"""


app = FastAPI(
    title="WalOUSMàJ API",
    description=description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "SPW Helpdesk",
        "email": "helpdesk.carto@spw.wallonie.be",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)


templates = Jinja2Templates(directory="walousmaj/api/templates")
app.mount("/static", StaticFiles(directory="walousmaj/api/static"), name="static")


@app.post("/launch", tags=["Launch"])
async def launch(config: ConfigValidator):
    from multiprocessing import Process

    from walousmaj.main import main

    p = Process(target=main, args=(config.dict(), False))
    p.start()
    return {}


@app.post("/resume", tags=["Resume"])
async def resume():
    from multiprocessing import Process

    from walousmaj.main import main

    p = Process(target=main, args=(None, True))
    p.start()
    return {}


@app.get("/config", response_class=FileResponse, tags=["Config"])
async def get_config_file():
    last_job = get_last_job()
    if (
        last_job
        and last_job["status"] == Status.ONGOING.name
        and last_job["config_filepath"]
        and Path(last_job["config_filepath"]).exists()
    ):
        config_filepath = last_job["config_filepath"]
        output_filename = "walous_config_en_cours.yml"
    elif Path(CONFIG_DEFAULT_FILEPATH).exists():
        config_filepath = CONFIG_DEFAULT_FILEPATH
        output_filename = "walous_config_defaut.yml"
    else:
        raise HTTPException(status_code=404, detail="Config file not found")
    response = FileResponse(config_filepath, media_type="text/yml")
    response.headers["Content-Disposition"] = f"attachment; filename={output_filename}"
    return response


@app.get("/config_doc", response_class=JSONResponse, tags=["Documentation Config"])
async def get_config_doc():
    return JSONResponse(content=json.loads(ConfigValidator.schema_json()))


@app.get("/status", response_class=HTMLResponse, tags=["Status"])
async def get_status(request: Request):
    attributes = [
        "position",
        "stage",
        "status",
        "progress",
        "remaining_time",
        "last_update",
    ]
    return templates.TemplateResponse(
        TEMPLATE_STAGE_TABLE_PATH,
        {
            "request": request,
            "attributes": attributes,
            "stages": get_data(STAGE_TABLE_NAME, attributes),
        },
    )


@app.get("/details", response_model=List[Maille], tags=["Détails"])
def get_details():
    attributes = [
        "OBJECTID",
        "IMAGE_NAME",
        "stage",
        "status",
        "error",
        "last_update",
    ]
    return get_data(MAILLE_TABLE_NAME, attributes)


@app.get("/details_table", response_class=HTMLResponse, tags=["Détails Table"])
async def get_details_table(request: Request):
    attributes = [
        "OBJECTID",
        "IMAGE_NAME",
        "stage",
        "status",
        "error",
        "last_update",
    ]
    return templates.TemplateResponse(
        TEMPLATE_MAILLE_TABLE_PATH,
        {
            "request": request,
            "attributes": attributes,
            "mailles": get_data(MAILLE_TABLE_NAME, attributes),
        },
    )


@app.get("/details_export", response_class=StreamingResponse, tags=["Détails Export"])
async def get_details_export():
    stream = io.StringIO()
    attributes = [
        "OBJECTID",
        "IMAGE_NAME",
        "stage",
        "status",
        "error",
        "last_update",
    ]
    pd.DataFrame(get_data(MAILLE_TABLE_NAME, attributes)).to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=walous_status.csv"
    return response


@app.get("/log", response_class=FileResponse, tags=["Log"])
async def get_log_file():
    if not Path(LOG_FILEPATH).exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    response = FileResponse(LOG_FILEPATH, media_type="text/log")
    response.headers["Content-Disposition"] = "attachment; filename=walous_log.log"
    return response


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8080)
