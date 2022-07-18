"""WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>."""
from pydantic import BaseModel


class Maille(BaseModel):
    objectid: str
    image_name: str
    etape: str
    status: str
    erreur: str
    derniere_modification: str

    class Config:
        orm_mode = True
