"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Script pour générer une matrice de confusion. WalousMàJ2022.
"""
from typing import Tuple

import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.collections import QuadMesh
from matplotlib.colors import LinearSegmentedColormap
from sklearn.metrics import confusion_matrix

"""
Ce script génère une matrice de confusion sur base des prédictions du modèle et des photo-interprétations. Les labels des prédictions et photo-interprétations sont regroupés par strate (100 à 800) pour respecter l'approche proposée dans Walous 2018.

Les données d'entrée doivent être fournies via un Shapefile (`SHAPEFILE_INPUT_PATH`) qui doit contenir les deux attributs suivants:
    - PHOTOINT: Label d'une classe Walous obtenue suite à une photo-interprétation d'un expert sur base des orthophotos (double ou simple label).
    - prediction: Label d'une classe Walous prédite par le modèle à évaluer.


"""

# Paramètres
SHAPEFILE_INPUT_PATH = "data.shp"  # Chemin vers les données d'entrée
CONFUSION_MATRIX_OUTPUT_PATH = "confusion_matrix.png"  # Chem. v. les données de sortie

# Tables de conversion
STRATE_TITLES = {
    100: "Revet. art. au sol",
    200: "Const. art. hors sol",
    300: "Eau",
    400: "Couv. herb. permanent",
    500: "Couv. herb. rotation",
    600: "Sols nus",
    700: "Feuillus",
    800: "Résineux",
    900: "Ombres",
    1000: "Changements",
}
LABELS_STRATES = {
    1: 100,
    2: 200,
    3: 100,
    4: 600,
    5: 300,
    6: 500,
    7: 400,
    8: 800,
    9: 700,
    11: 100,
    15: 300,
    18: 800,
    19: 700,
    28: 800,
    29: 700,
    31: 100,
    38: 800,
    39: 700,
    51: 100,
    55: 300,
    58: 800,
    59: 700,
    62: 200,
    71: 100,
    73: 100,
    75: 300,
    80: 800,
    81: 100,
    83: 100,
    85: 300,
    90: 700,
    91: 100,
    93: 100,
    95: 300,
}


def cmap_grey_to_pink():
    colors = ["#EFEFEF", "#F06185"]
    return LinearSegmentedColormap.from_list("asl", colors, N=100)


def labels_to_strates(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf["y_true"] = gdf["PHOTOINT"].astype(int).map(LABELS_STRATES.get)
    gdf["y_pred"] = gdf["prediction"].astype(int).map(LABELS_STRATES.get)
    return gdf


def configcell_text_and_colors(
    ax,
    cm: np.ndarray,
    fontsize: int,
    precision: int = 2,
    total_cell_color: Tuple[int, int, int] = (255, 0, 0),
    show_null_values: bool = False,
    show_cell_percent: bool = False,
):
    quadmesh = ax.findobj(QuadMesh)[0]
    facecolors = quadmesh.get_facecolors()

    txt_obj_to_add = []
    txt_obj_to_delete = []

    total_x = np.sum(cm, axis=0)
    total_y = np.sum(cm, axis=1)
    total_all = np.sum(total_y)
    diag = cm.diagonal()

    h, w = cm.shape
    assert h == w

    for color_idx, txt_obj in enumerate(ax.collections[0].axes.texts):
        x, y = [int(x - 0.5) for x in txt_obj.get_position()]

        # Totaux (i.e.: dernière ligne et/ou dernière colonne)
        if (x == (w - 1)) or (y == (w - 1)):
            if (x == w - 1) and (y == w - 1):  # Cellule en bas à droite
                total_p = total_all
                tp = np.sum(diag[:-1])
            elif x == w - 1:  # Cellule total de la ligne
                total_p = total_y[y]
                tp = diag[y]
            elif y == w - 1:  # Cellule total de la colonne
                total_p = total_x[x]
                tp = diag[x]

            accuracy = (tp / total_p) * 100 if total_p != 0 else 0.0
            if int(accuracy) in [100, 0]:
                accuracy_str = f"{int(accuracy)}%"
            else:
                accuracy_str = f"{accuracy:.{precision}f}%"

            # txt_obj à supprimer
            txt_obj_to_delete.append(txt_obj)

            # txt_obj à ajouter
            font_prop = fm.FontProperties(weight="bold", size=fontsize)
            txt_kwargs = {
                "ha": "center",
                "va": "center",
                "gid": "sum",
                "fontproperties": font_prop,
            }
            texts = [str(int(total_p)), accuracy_str]
            colors = ["w", "darkgrey"]
            y_offsets = [-0.2, 0.2]
            for txt_str, color, y_offset in zip(texts, colors, y_offsets):
                new_text_obj = {
                    "x": txt_obj._x,
                    "y": txt_obj._y + y_offset,
                    "s": txt_str,
                    "color": color,
                    **txt_kwargs,
                }
                txt_obj_to_add.append(new_text_obj)

            # Mise à jour de la couleur de fond pour les cellules avec les totaux
            facecolors[color_idx] = [x / 255 for x in total_cell_color] + [1.0]

        else:
            cell_value = int(cm[y][x])
            if cell_value > 0:
                if show_cell_percent:
                    cell_percent = (float(cell_value) / total_all) * 100
                    txt = f"{cell_value}\n{cell_percent:.{precision}f}%"
                else:
                    txt = str(cell_value)
            else:
                if show_null_values:
                    txt = "0\n0.0%" if show_cell_percent else "0"
                else:
                    txt = ""
            txt_obj.set_text(txt)
            txt_obj.set_fontsize(7)

            if x == y:  # Diagonale
                txt_obj.set_color("w")
            else:
                txt_obj.set_color("black")

    for txt_obj in txt_obj_to_delete:
        txt_obj.remove()
    for txt_obj in txt_obj_to_add:
        ax.text(**txt_obj)

    return ax


def make_confusion_matrix(
    cm: np.ndarray,
    output_path: str,
    cbar: bool = False,
    axeslabels: bool = True,
    ticklabels_map: dict = {},
    figsize: Tuple[float, float] = None,
    cmap: LinearSegmentedColormap = cmap_grey_to_pink(),
    total_cell_color: Tuple[int, int, int] = (15, 43, 120),
    fontsize: int = 7,
    precision: int = 2,
    show_cell_percent: bool = False,
    heatmap_mode: str = "row-wise",  # ["row-wise", "column-wise", "overall"]
    title: str = None,
) -> str:
    if figsize is None:
        figsize = plt.rcParams.get("figure.figsize")

    # Insertion d'une ligne et colonne temporaires pour les totaux
    for i in [0, 1]:
        total = np.zeros((1, cm.shape[0]))
        if i:
            total = total.T
        cm = np.concatenate((cm, total), axis=i)

    # Preparation de la matrice de confusion et pondération en fonction des poids, par
    # ligne ou par colonne
    if heatmap_mode == "overall":
        heatmap_cm = cm
    elif heatmap_mode == "column-wise":
        np.seterr(divide="ignore", invalid="ignore")
        heatmap_cm = np.nan_to_num(cm / np.sum(cm, axis=0))
    elif heatmap_mode == "row-wise":
        np.seterr(divide="ignore", invalid="ignore")
        heatmap_cm = np.nan_to_num(cm / np.expand_dims(np.sum(cm, axis=1), axis=1))
    else:
        raise ValueError(
            "Value for `heatmap_mode` not supported. Expected: "
            "[overall, column-wise, row-wise]"
        )

    # Création de la heatmap de base
    fig = plt.figure(figsize=figsize)
    ax1 = fig.gca()  # Obtiens l'axe utilisé
    ax1.cla()  # Efface le plot existant
    ax = sns.heatmap(
        heatmap_cm,
        annot=True,
        fmt="",
        cmap=cmap,
        cbar=cbar,
        xticklabels=True,
        yticklabels=True,
    )

    # Replacement des traits aux axes
    for axis_name, total_name, rot, align in zip(
        ["x", "y"], ["PA", "UA"], [20, 0], ["left", "right"]
    ):
        labels = [tl.get_text() for tl in eval(f"ax.get_{axis_name}ticklabels()")][:-1]
        last_label = total_name
        if ticklabels_map:
            labels = [ticklabels_map.get(l, ticklabels_map[int(l)]) for l in labels]
        labels.append(last_label)
        kwargs = {"rotation": rot, "fontsize": 8, "ha": "align"}
        unpacked_kwargs = ", ".join([k + "=" + str(v) for k, v in kwargs.items()])
        eval(f"ax.set_{axis_name}ticklabels(labels, {unpacked_kwargs})")

    # Ajustement de la couleur des cellules et calcule des totaux
    ax = configcell_text_and_colors(
        ax,
        cm,
        fontsize=fontsize,
        precision=precision,
        total_cell_color=total_cell_color,
        show_cell_percent=show_cell_percent,
    )

    # Adaptation des axes et des labels
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    if axeslabels:
        plt.ylabel("Classes réelles")
        plt.xlabel("Classes prédites")
    if title:
        plt.title(title)

    plt.tight_layout()
    fig.savefig(output_path, dpi=500)
    return output_path


if __name__ == "__main__":
    gdf = gpd.read_file(SHAPEFILE_INPUT_PATH)
    gdf = labels_to_strates(gdf)
    cf_matrix = confusion_matrix(
        gdf["y_true"],
        gdf["y_pred"],
        sample_weight=gdf["poids"],
        labels=list(range(100, 801, 100)),
    )
    make_confusion_matrix(
        cm=cf_matrix,
        output_path=CONFUSION_MATRIX_OUTPUT_PATH,
        heatmap_mode="column-wise",
        ticklabels_map={k / 100 - 1: v for k, v in STRATE_TITLES.items()},
    )
