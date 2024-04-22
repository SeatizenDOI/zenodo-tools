# Zenodo-tools

## Configuration

Pour utiliser ce dépôt, il vous faut un fichier de config.json à la racine du projet contenant votre propre ACCESS_TOKEN :

```json
{
    "ACCESS_TOKEN": "ACCESS_TOKEN",
    "ZENODO_LINK": "https://sandbox.zenodo.org/api/deposit/depositions"
}
```

## TODO

- Faire la correspondance gbif du fichier d'annotation.
- Ajouter un script qui permet de mettre à jour le zenodo metadata global ( définir ce qu'il faut mettre dedans )