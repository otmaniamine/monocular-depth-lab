# Applications de la profondeur monoculaire

Cinq applications réutilisent les modèles préentraînés Small déjà installés. Aucun entraînement, aucun LiDAR et aucune nouvelle dépendance lourde. Elles transforment une carte de profondeur en **résultat visuel et proposition d'action**.

Ouvrir la [galerie des résultats](index.html) dans un navigateur, ou consulter les exemples ci-dessous directement dans GitHub.

| Application | Problème traité | Résultat / action proposée |
|---|---|---|
| [1. Navigation routière](01_navigation_routiere/README.md) | Repérer des surfaces proches dans une vue de rue | Zones annotées, alerte simulée, revue d'une vidéo |
| [2. Robot aspirateur](02_robot_aspirateur/README.md) | Examiner des surfaces saillantes au-dessus du sol | Candidats géométriques et demande de vérification |
| [3. Traitement d'image](03_traitement_image/README.md) | Atténuer les éléments éloignés du sujet | Flou progressif guidé par la profondeur |
| [4. Entreprise : aménagement](04_entreprise_amenagement/README.md) | Discuter l'implantation d'un meuble avant une visite | Gabarit 3D projeté avec masquage par le décor |
| [5. Industrie : passage](05_industrie_passage/README.md) | Examiner un passage entre des stocks | Zones à inspecter et rapport de revue humaine |

## Lancer les cinq démonstrations

Depuis la racine du projet dans le terminal **PowerShell de VS Code** :

```powershell
.\.venv\Scripts\python.exe -m application.run --demo all
```

Les sorties de calcul sont placées dans `results/application/`. Chaque dossier contient `index.html` pour voir les images, `RAPPORT.md` pour les actions, `rapport.json` pour les mesures, les masques et les profondeurs brutes `.npy`. Les vidéos ont aussi `video_annotee.mp4`, une version WebM pour le navigateur et `chronologie.csv`.

Pour ouvrir le premier rapport :

```powershell
Start-Process ".\results\application\01_navigation_routiere\index.html"
```

Les photographies et les deux extraits publics sont inclus dans `application/assets/`. Les exemples sélectionnés dans les cinq sous-dossiers permettent de consulter les résultats sans relancer le modèle. Pour retélécharger les médias publics, si nécessaire :

```powershell
.\.venv\Scripts\python.exe -m application.prepare_assets --video
```

Cette commande peut télécharger environ 110 Mo de vidéos sources dans `results/`, puis conserver seulement de courts extraits redimensionnés dans `application/assets/`. Elle n'est pas nécessaire pour les essais habituels.

## Utiliser vos propres médias

Mettre les fichiers dans `inputs/`, puis remplacer le nom dans une des commandes :

```powershell
.\.venv\Scripts\python.exe -m application.run --app robot --input ".\inputs\salon.jpg"
.\.venv\Scripts\python.exe -m application.run --app route --input ".\inputs\trajet.mp4" --every 10 --max-frames 30
.\.venv\Scripts\python.exe -m application.run --app photo --input ".\inputs\produit.jpg" --focus 0.50 0.55
.\.venv\Scripts\python.exe -m application.run --app entreprise --input ".\inputs\piece.jpg" --anchor 0.70 0.85 --dimensions 0.8 0.7 0.55
.\.venv\Scripts\python.exe -m application.run --app industrie --input ".\inputs\atelier.jpg"
```

Chaque commande est indépendante. Le programme accepte une photo ou une vidéo, pas un dossier. Les modes `photo` et `entreprise` traitent uniquement les photos. L'argument `--output` permet de séparer plusieurs essais au lieu d'écraser les sorties portant les mêmes numéros.

Les coordonnées sont des proportions de l'image : X de gauche à droite, Y de haut en bas. `(0.5, 0.5)` est le centre. `--seed X0 Y0 X1 Y1` désigne un rectangle **sur un sol visible et approximativement plan**, et `--roi X0 Y0 X1 Y1` la zone à examiner. Adapter ces rectangles à chaque scène. Une mauvaise zone de sol peut invalider l'analyse ou produire un résultat trompeur.

```powershell
.\.venv\Scripts\python.exe -m application.run --app robot --input ".\inputs\salon.jpg" --seed 0.30 0.80 0.65 0.96 --roi 0.10 0.45 0.90 0.98
```

`--fov` modifie le champ horizontal supposé ; il ne calibre pas la caméra. Pour cette première version des applications, les paramètres intrinsèques exacts ne sont pas acceptés. La commande existante `reconstruct.py` permet séparément une reconstruction avec `--fx`, `--fy`, `--cx`, `--cy`.

## Ce que la navigation réalise

Photo/vidéo → profondeur estimée → projection 3D → estimation RANSAC du sol dans la zone choisie → sélection de surfaces au-dessus de ce plan → composantes connexes → secteurs gauche/centre/droite → état et proposition d'action.

Les rectangles rouges regroupent des **surfaces géométriques**, pas des objets reconnus. Un mur et un meuble peuvent appartenir au même groupe. La zone de surveillance n'est pas une trajectoire calculée. Les seuils en mètres sont appliqués à une échelle estimée, sans validation de mesure. Ils servent à expérimenter, pas à définir une distance de freinage.

| État | Sens |
|---|---|
| `ABSTENTION` | Entrée déclarée inadaptée, profondeur insuffisante ou hypothèse de sol rejetée |
| `ALERTE_SIMULEE` | Surface candidate sous le seuil de proximité choisi |
| `VIGILANCE` | Surfaces candidates dans la zone surveillée, hors seuil d'alerte |
| `A_CONFIRMER` | Aucun candidat dans ces paramètres ; **cela ne prouve pas un passage libre** |

En vidéo, l'état temporel confirme une alerte après trois vues analysées consécutives. Une vue inconnue remet ce compteur à zéro. Les images sont traitées indépendamment par Depth Anything V2 : ce filtre n'assure ni une profondeur temporellement stable, ni un suivi d'objets, ni une estimation de vitesse ou de temps avant collision. Les horodatages proviennent de la cadence de la source et l'extrait annoté conserve la cadence réduite de l'échantillonnage. Le calcul est hors ligne, pas une caméra temps réel.

## Portée et validation

Cette version est un **prototype de perception pour essais hors ligne**. Elle ne pilote aucun véhicule, robot ou machine. Elle ne détecte pas les trous et les marches descendantes. Une seule vue ne révèle pas les zones cachées ; reflets, vitres, câbles et petits obstacles peuvent être mal estimés ou retirés par le filtre de bruit. Une caméra basse de robot demande des essais spécifiques : la photo de logement fournie est prise depuis une hauteur humaine.

Les tests synthétiques vérifient des propriétés connues : sol seul non alarmant, patch surélevé détecté, mur rejeté comme sol, abstention sur profondeur absente, compteur temporel réinitialisé, effet de flou et occlusion du volume virtuel. Les essais sur médias réels vérifient le fonctionnement du parcours complet. **Aucune précision de détection ou de mesure n'a été évaluée sur un jeu de vérité terrain.**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

La valeur ajoutée est le passage de la profondeur brute à plusieurs traitements, avec sélection du sol, règles explicites, abstention, rapport et analyse vidéo. Le modèle de profondeur et la géométrie de projection proviennent des travaux existants. Voir les [sources et crédits](SOURCES.md).

Les entrées personnelles, poids, environnements et résultats de travail restent ignorés par Git. Seuls les médias publics crédités et une sélection de démonstrations sont conservés dans `application/`. Aucun chemin personnel n'est inscrit dans les rapports générés.
