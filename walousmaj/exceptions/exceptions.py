"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set de classes d'Exceptions/Erreurs.
"""
from walousmaj.utils.enums import StageOrder


class WalousMaJError(Exception):
    """Classe de base, liée à une étape, dont découle les autres exceptions."""

    def __init__(self, stage: StageOrder, message: str):
        self.stage = stage
        self.message = self.strip(message)
        super().__init__()

    def __str__(self):
        return f"Etape {self.stage.name.capitalize()}: {self.message}"

    @staticmethod
    def strip(message: str):
        return message.replace('"', "").replace("'", "")
