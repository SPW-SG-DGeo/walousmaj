# Installation
## Installation du package

Pour utiliser ce package, vous devez d'abord l'installer. Depuis la racine du package:

```bash
pip install .
```

Assurez-vous que les différentes dépendances mentionnées dans les fichiers `Pipfile` et `environment.yml` aient bien été installées.


## Utilisation du GPU

Le `Pipfile` installe PyTorch avec une version CUDA de 11.0. Si votre GPU ne supporte pas cette version, il faut adapter le `Pipfile` en conséquence.



## Création du docker
### Groupe d'utilisateurs

Afin de pouvoir lire les fichiers écrits par le container, l'utilisateur doit être dans le groupe `walous_grp` (group ID: 6060).
Si ce groupe n'existe pas encore sur la machine:

```bash
sudo addgroup --gid 6060 walous_grp
```

Pour rajouter l'utilisateur actuel dans le groupe:
```bash
sudo usermod -a -G walous_grp $USERNAME
```
### Permissions des volumes

Il faut monter 2 volumes: `/walous/input` et `/walous/output`. Afin que les utilisateurs du groupe `walous_grp` puissent lire/écrire dedans, il est nécessaire de changer les permissions:

```bash
sudo chown -R :walous_grp /walous/input /walous/output
sudo chmod -R 775 /walous/input /walous/output
```

Il faut également s'assurer que tout nouveau fichier créé dans le volume d'output héritent du groupe de celui-ci:

```bash
sudo chmod g+s /walous/output
```


### Construction et démarrage de l'image
Pour construire l'image depuis la racine du package:

```bash
docker build --tag walousimage --target runtime .
```

Ensuite, lancez le docker avec la commande suivante:

```bash
docker run --name walouscontainer --gpus all -v /walous/input:/home/walous/input -v /walous/output:/home/walous/output -p 8081:8080 walousimage:latest
```

Une API sera alors disponible sur `localhost:8081`. Veuillez changer la commande si le port `8081` est indisponible.

## Génération de la documentation

Pour générer une documentation au format HTML du code, rendez-vous dans le dossier `doc` et installer d'abord les dépendances nécessaires:

```bash
pip install -r requirements.txt -q
```

Ensuite, il vous suffira d'exécuter la commande suivante:

```bash
make html
```

La documentation se trouve maintenant dans le dossier suivant: `doc/_build/html`. Pour visualiser celle-ci, il vous suffit d'ouvrir le fichier `index.html` dans votre navigateur internet.
