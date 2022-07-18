ARG BASE_IMAGE=ubuntu:18.04

FROM ${BASE_IMAGE} as miniconda3
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        ccache \
        cmake \
        curl \
        gcc \
        git \
        libjpeg-dev \
        libpng-dev \
    && rm -rf /var/lib/apt/lists/*
ENV PATH /opt/conda/bin:$PATH
RUN curl -fsSL -v -o ~/miniconda.sh -O  https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && chmod +x ~/miniconda.sh \
    && ~/miniconda.sh -b -p /opt/conda \
    && rm ~/miniconda.sh \
    && /opt/conda/bin/conda clean -ya

FROM miniconda3 as base-img
# Ajout du group walous
ARG GID=6060
RUN addgroup --gid $GID walous_grp
# Ajout de l'utilisateur walous
RUN useradd --create-home walous
RUN usermod -a -G walous_grp walous
USER walous
WORKDIR /home/walous
# Création de l'environnement Conda
COPY --chown=walous environment.yml environment.yml
RUN conda env create -q -f environment.yml \
    && conda clean -afy
ENV CONDA_ENV /home/walous/.conda/envs/walous_env
# Rajout des binaries installés via conda dans le PATH
ENV PATH $CONDA_ENV/bin:$PATH
# Variables d'environement GDAL et PROJ
ENV GDAL_DATA $CONDA_ENV/share/gdal
ENV PROJ_LIB $CONDA_ENV/share/proj
ENV _CONDA_SET_PROJ_LIB $CONDA_ENV/share/proj
# Ajout de la grille LB72->LB08 dans le dossier de PROJ
COPY --chown=walous proj/be_ign_bd72lb72_etrs89lb08.tif $CONDA_ENV/share/proj/be_ign_bd72lb72_etrs89lb08.tif
# La variable suivante permet de télécharger les projections manquantes si nécesaire
ENV PROJ_NETWORK ON
# Installation des dépendances Pip
COPY --chown=walous Pipfile Pipfile
COPY --chown=walous Pipfile.lock Pipfile.lock
RUN pip install --no-cache-dir pipenv \
    && pipenv install --deploy --system
COPY --chown=walous walousmaj walousmaj
COPY --chown=walous setup.py setup.py
COPY --chown=walous main.py main.py
COPY --chown=walous README.md README.md
RUN pip -q install --no-cache-dir -e .

FROM base-img as runtime
# Informe Docker que le container écoute au port 8080
EXPOSE 8080
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8080", "walousmaj.api.main:app"]
