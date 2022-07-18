# Quickstart

Pour utiliser ce package, vous devez d'abord l'installer. Assurez vous d'avoir suivi les instructions du fichier `INSTALL.md`.

Ensuite, pour lancer l'exécution d'un job, vous devez d'abord configurer ce job. Utiliser le fichier `walousmaj/assets/config/config.yml` comme exemple et dupliquez le pour créer votre propre fichier de configuration.

Une fois ceci fait, vous pouvez exécuter votre job. Depuis la racine du package:

```bash
python main.py -cf PATH/VERS/VOTRE/CONFIG.yml
```

Alternativement, vous pouvez également utiliser la solution depuis un `docker`:
Pour ceci, depuis la racine du package:

```bash
docker build -t walousimage .
```

Une fois l'`image` du `container` créée, il vous faut maintenant lancer le `docker` et y attacher les `volumes` contenant les données d'entrée (e.g.: Orthophotos, MNT, MNS, ...)
```bash
docker run --name walouscontainer --gpus all -v /walous/input:/home/walous/input -v /walous/output:/home/walous/output -p 8081:8080 walousimage:latest
```

Rendez-vous maintenant, sur la page d'accueil de l'API: http://localhost:8081/docs