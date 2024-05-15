# Zenodo-tools

## Create env
```
    conda create env --file zenodo_env.yml
    conda activate zenodo_env
```

## Configuration

Pour utiliser ce dépôt, il vous faut un fichier de config.json à la racine du projet contenant votre propre ACCESS_TOKEN :

```json
{
    "ACCESS_TOKEN": "ACCESS_TOKEN",
    "ZENODO_LINK": "https://sandbox.zenodo.org/api/deposit/depositions"
}
```

# Choix réaliser pour la compression des fichiers

Il est possible de publier deux types de données.

- les données brutes (RAW_DATA)

Les données brutes ne sont pas accessibles au public. Certaines sessions comporte plus de 50Go de données brutes or zenodo limite un dépot de fichier à 50Go par version.
Pour éviter ce problème, les dossiers sont découpés en sous archive et auront vocation à être uploadé dans différentes versions.

Actuellement, il n'y a que le dossier DCIM qui dépasse les 50 Go. Donc ce traitement ne s'applique à ce dossier.

Exemple :

Si nous avons ces fichiers à envoyer
```txt
DCIM.zip # 50 Go
DCIM_2.zip # 19 Go
GPS.zip # 170 Mo
SENSORS.zip # 2 Go
```

Sur zenodo cela correspondra à :
version RAW_DATA 

```txt
DCIM.zip
```
version RAW_DATA_2

```txt
DCIM_2.zip
GPS.zip
SENSORS.zip
```

- les données calculées (PROCESSED_DATA)


## TODO

- Faire la correspondance gbif du fichier d'annotation.
- Ajouter un script qui permet de mettre à jour le zenodo metadata global ( définir ce qu'il faut mettre dedans )
- Trier les créateurs / collaborateurs


## Deposit général

- session_doi.csv
Contient deux colonnes : nom de la session, doi pointant vers la dernière version du deposit associé à la session
