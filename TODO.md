# Seaatizen manager

Le but de cet outil est de proposer un moyen d'ajouter, gérer et d'exporter des sessions seatizen pour tous types d'utilisateurs.

Il permet de gérer le dépôt zenodo associé. Celui contient un geopackage qui concentre toute la donnée et des fichiers csv qui sont des exports du geopackage à un instant t. Un geopackage est une base de données SQLite avec une dimension géospatiale en plus.

Un utilisateur expérimenté pourra par exemple utilisé le .gpkg qui contient toutes les données du projet et l'utilisé pour réaliser ses propres requêtes.

## Gestion du dépot global

/!\ Pour mettre à jour la base de données, il faut que les sessions soit en ligne sur zenodo et il faut aussi avoir la session en local /!\

Soit on télécharge ce qu'il y a en ligne

1.1.1 On télécharge la base de données. S'il elle n'est pas présente => 1.2 sinon 2.1

1.2 On génère la base de données

2.1.1 Pour chaque session, on récupère le conceptrecid et le doi de version des frames et des predictions (Comparaison des sums md5 frames.zip et predictions.zip).

2.1.2 On regarde s'il existe un deposit avec ce conceptrecid. Si oui on le récupère, sinon on le crée

2.1.3 On regarde s'il existe une version avec les frames. Si non, on crée la version et on ajoute les frames.

2.1.4 On regqrde s'il existe une version avec les prédictions. Si non on crée la version.

2.1.5 On regarde s'il existe le modèle associé aux prédictions. Si non, on l'ajoute ainsi que ses classes.

2.1.6 On ajoute les prédictions liés au frames.

2.1.7 

Comment gérer deux models de multilabel différent

## Import

On va vouloir importer des données après une campagne plancha. Il faut que les sessions soient traités et mise en ligne sur Zenodo.

On pourrait aussi vouloir importer des données après un effort d'annotation.

Un script est mis à disposition pour regénérer la base de données. Mais, normalement, le script a pour but de la mettre à jour.

Déroulement de l'import d'une session :

- Il faut récupérer le conceptrecid ainsi que les doi de chaque version.
- On va ensuite zipper le dossier METADATA et le dossier FRAMES pour avoir le md5 de chaque dossier et le comparer avec ceux en ligne pour récupérer le bon doi de version
    * predictions dans une version et frames dans une autre version
    * frames mais enfaite récupérer le nom du dossier en lisant le fichier metadata.csv/relative_path
- Une fois qu'on connait le doi de version pour les frames et les prédictions, on commence à peupler les tables
    * deposit : conceptrecid, 

/!\ Le script ne prends pas en compte la mise à jour de 2 fichier PROCESSED_DATA_FRAMES.zip. En effet, on se base sur les changements fais en local. Donc si on a 3 dossier FRAMES et 4 dossier IA, on prendra les checksums de celui en local /!\

Maintenant, si on souhaite réaliser un effort d'annotation.

Importer de nouveaux models et importer de nouveaux labels

# Export

On peut faire des exports csv basiques :
- metadata_images.csv
- session_doi.csv
- metadata_annotation.csv
- fichier qui montre l'emprise de chaque session pour toutes les sessions.

On peut aussi faire des exports de fichiers gpkg exploitable (centralisé tous les sessions de saint leu pour avoir l'emprise par exemple)

Faire olutot un session_doi.csv en pdf