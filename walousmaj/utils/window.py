"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour extraire des fenêtres de lecture.
"""
from itertools import product
from random import randrange
from typing import Generator, Tuple

from rasterio import windows


def iter_windows(
    input_height: int, input_width: int, window_height: int, window_width: int
) -> Generator[windows.Window, None, None]:
    """Générateur de fenêtres (au format rasterio) aux dimensions spatiales spécifiques.

    :param input_height: Hauteur de la donnée source.
    :type input_height: int
    :param input_width: Largeur de la donnée source.
    :type input_width: int
    :param window_height: Hauteur de la fenêtre.
    :type window_height: int
    :param window_width: Largeur de la fenêtre.
    :type window_width: int
    :yield: Rasterio's Window aux dimensions spécifiées.
    :rtype: Generator[windows.Window, None, None]
    """
    max_col_off = input_width - window_width + 1
    max_row_off = input_height - window_height + 1
    offsets = product(
        range(0, input_width, window_width), range(0, input_height, window_height)
    )
    for col_off, row_off in offsets:
        if col_off >= max_col_off:
            col_off = input_width - window_width
        if row_off >= max_row_off:
            row_off = input_height - window_height
        window = windows.Window(
            col_off=col_off, row_off=row_off, width=window_width, height=window_height
        )
        yield window


def iter_windows_with_overlap(
    input_height: int,
    input_width: int,
    window_size: int,
    overlap: int = 0,
) -> Generator[Tuple[windows.Window, windows.Window, Tuple[slice, slice]], None, None]:
    """Générateur de fenêtres de lecture et d'écriture (au format rasterio et numpy).

    :param input_height: Hauteur de la donnée source.
    :type input_height: int
    :param input_width: Largeur de la donnée source.
    :type input_width: int
    :param window_size: Dimensions spatiales de la fenêtre. Uniquement des fenêtres
        carrées.
    :type window_size: int
    :param overlap: Taille (en pixel) du chevauchement entre fenêtres adjacentes. Doit
        être un multiple de 2. Pas de chevauchement par défaut.
    :type overlap: int, optional
    :yield: Tuple dont le premier élément est la fenêtre de lecture pour extraire la
        fenêtre de la donnée source, le deuxième élément est la fenêtre d'écriture (i.e.
        sans la moitié du chevauchement sauf pour les bords) au format rasterio, et le
        dernier élément est la même fenêtre mais au format numpy.
    :rtype: Generator[Tuple[windows.Window, windows.Window, Tuple[slice, slice]], None, None]
    """
    stride = window_size - overlap
    half_overlap = overlap // 2
    max_col_off = input_width - window_size + 1
    max_row_off = input_height - window_size + 1
    offsets = product(range(0, input_width, stride), range(0, input_height, stride))
    for col_off, row_off in offsets:
        x_min = 0 if col_off == 0 else half_overlap
        y_min = 0 if row_off == 0 else half_overlap
        x_max, y_max = [window_size - half_overlap] * 2
        if col_off >= max_col_off:
            col_off = input_width - window_size
            x_max += half_overlap
        if row_off >= max_row_off:
            row_off = input_height - window_size
            y_max += half_overlap

        window_read = windows.Window(
            col_off=col_off, row_off=row_off, width=window_size, height=window_size
        )
        window_write = windows.Window(
            col_off=col_off + x_min,
            row_off=row_off + y_min,
            width=x_max - x_min,
            height=y_max - y_min,
        )
        predictions_slices = (slice(y_min, y_max), slice(x_min, x_max))
        yield window_read, window_write, predictions_slices


def get_random_window(
    ortho_shape: Tuple[int, int], window_shape: Tuple[int, int]
) -> windows.Window:
    """Obtenir une fenêtre (au format rasterio) aléatoire aux dimensions spatiales
    spécifiques.

    :param ortho_shape: Hauteur et largeur de la donnée source.
    :type ortho_shape: Tuple[int, int]
    :param window_shape: Hauteur et largeur désirée pour la fenêtre.
    :type window_shape: Tuple[int, int]
    :return: Rasterio's Window aux dimensions spécifiées.
    :rtype: windows.Window
    """
    o_height, o_width = ortho_shape
    w_height, w_width = window_shape
    col_off = randrange(o_width - w_width)
    row_off = randrange(o_height - w_height)
    return windows.Window(
        col_off=col_off, row_off=row_off, width=w_width, height=w_height
    )
