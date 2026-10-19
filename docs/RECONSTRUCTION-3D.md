# Reconstruction 3D depuis une photo

## Utilisation

1. Placez vos photos dans `inputs/`.
2. Double-cliquez sur `Reconstruire-3D.cmd` et choisissez intérieur ou extérieur.
3. Le premier résultat s'ouvre dans votre navigateur. Glissez pour tourner et utilisez la molette ou le curseur pour zoomer. Les boutons Face, Vue oblique et Profil changent le point de vue.

Pour une démonstration publique sans utiliser de photo personnelle, lancez `Demo-3D.cmd`.

Depuis PowerShell, à la racine du projet :

```powershell
# Scène intérieure
.\.venv\Scripts\python.exe .\reconstruct.py --input .\inputs\photo.jpg --model indoor --open

# Scène extérieure, en conservant les profondeurs entre 0,1 et 35 mètres estimés
.\.venv\Scripts\python.exe .\reconstruct.py --input .\inputs\photo.jpg --model outdoor --max-depth 35 --open

# Reproduire l'exemple de l'escalier intérieur
.\.venv\Scripts\python.exe .\reconstruct.py --input .\source\assets\examples\demo15.jpg --model indoor --open
```

Un dossier est accepté, les vidéos ne le sont pas dans cette première version. Chaque photo est reconstruite séparément. Les photos du dossier sont traitées successivement ; elles ne sont pas fusionnées.

## Fichiers créés

Les sorties vont dans `results/3d/` et restent locales :

| Extension | Contenu |
| --- | --- |
| `.html` | Visionneuse 3D autonome, utilisable hors ligne par double-clic, sans CDN ni envoi de médias |
| `.ply` | Nuage binaire XYZ/RGB compatible avec les lecteurs PLY ; repère caméra X droite, Y bas, Z devant |
| `.npy` | Profondeur métrique brute à la résolution de traitement, avant filtrage |
| `.npz` | Points XYZ filtrés, couleurs RGB et pixels correspondants |
| `.json` | Paramètres de caméra, filtrage, nombre de points et contrôle de projection ; aucun chemin source absolu |
| `.png` | Aperçu du nuage sous un angle oblique |
| `_depth.png` | Image et profondeur colorée ; le noir indique les points écartés par les filtres |

La visionneuse utilise au plus 120 000 points ; l'export PLY conserve tous les points filtrés et échantillonnés. Elle recentre et réduit la géométrie pour l'affichage, sans modifier les coordonnées exportées.

## Géométrie utilisée

Les modèles métriques Small intérieur et extérieur sont déjà disponibles dans le projet. Ils prédisent une profondeur axiale `Z` pour chaque pixel `(u, v)`. La conversion utilise le modèle de caméra perspective :

```text
X = (u - cx) × Z / fx
Y = (v - cy) × Z / fy
Z = profondeur estimée
```

La couleur du pixel est attachée au point `(X, Y, Z)`. Il faut utiliser la profondeur brute, pas les couleurs de la carte de visualisation. `Z` est la profondeur le long de l'axe optique ; la distance au centre de la caméra serait `sqrt(X² + Y² + Z²)`, avec les mêmes limites de précision que la profondeur estimée.

Si la caméra est inconnue, le programme suppose un champ horizontal de 60 degrés, des pixels carrés et un centre optique au centre de l'image. Ce choix est explicitement marqué comme estimé dans la visionneuse et les métadonnées. Il ne constitue pas une calibration.

Pour une photo calibrée, fournissez `--fx`, `--fy` et, si connus, `--cx`, `--cy` en pixels de la photo originale. Exemple de syntaxe avec des valeurs illustratives :

```powershell
.\.venv\Scripts\python.exe .\reconstruct.py --input .\inputs\photo.jpg --model indoor --fx 1200 --fy 1200 --cx 959.5 --cy 539.5 --open
```

Ne réutilisez pas ces valeurs sans calibration de votre caméra. Le programme adapte les paramètres au redimensionnement en respectant les centres des pixels : `fx' = sx × fx`, `cx' = sx × (cx + 0,5) - 0,5` (idem pour Y).

## Contraintes et choix de cette version

- Une seule photo décrit les surfaces visibles : l'arrière d'un objet et les zones masquées restent absents. En tournant, des trous apparaissent. Aucun remplissage génératif n'est appliqué.
- La profondeur est une prédiction IA. L'échelle en mètres et les dimensions ne sont pas validées avec des mesures réelles. Une caméra calibrée ne corrige pas les erreurs du modèle.
- Une mauvaise focale déforme les proportions. Les objectifs grand-angle et la distorsion doivent être corrigés en amont ; cette version attend une image rectifiée et ne corrige pas la distorsion.
- Les vitres, miroirs, éléments fins, contours et arrière-plans très lointains peuvent produire des erreurs. Le seuil de profondeur limite les points lointains ; le filtre de discontinuité peut retirer certains vrais détails fins.
- Les modèles relatifs ne fournissent pas directement de profondeur métrique. Cette première reconstruction prend uniquement les modèles `indoor` et `outdoor`.
- Le CPU exécute le réseau. La visionneuse utilise WebGL pour dessiner les points et affiche un message d'erreur si WebGL est indisponible. Aucun paquet Open3D supplémentaire n'est requis.
- Par défaut : image limitée à 960 pixels sur le plus grand côté, inférence 392, un point tous les trois pixels par axe. `--stride 2` augmente la densité ; `--stride 4` l'allège. `--edge-threshold 0` désactive le filtre aux contours.

Pour une reconstruction plus complète, l'étape suivante serait d'utiliser plusieurs photos avec recouvrement prises depuis différentes positions, puis d'estimer leurs poses et de fusionner la géométrie. Cela exige une autre chaîne de traitement, par exemple SfM/MVS, et davantage de calcul.

## Contribution du projet et validation

Le dépôt officiel Depth Anything V2 fournit déjà un script de projection vers PLY. La contribution de cette version est l'intégration locale : paramètres de caméra explicites et adaptés au redimensionnement, filtrage, export avec métadonnées, visionneuse hors ligne et lanceur simple. La géométrie perspective est une méthode standard, pas un nouvel algorithme inventé ici.

Les tests numériques couvrent un plan de profondeur connue, le retour des points vers leurs pixels, la cohérence du redimensionnement, les profondeurs invalides, les discontinuités et le format PLY :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Les tests navigateur optionnels nécessitent Playwright et Chrome. Ils vérifient le rendu effectif des points, les boutons de vue, le glissement, le zoom, l'absence de débordement mobile et les erreurs JavaScript :

```powershell
node tests/check_viewer.cjs results/3d/demo15_indoor.html
```

Le retour vers les pixels valide la mise en œuvre mathématique. Il ne mesure pas la justesse de la profondeur dans la scène réelle.

## Sources techniques

- [Depth Anything V2 : modèles métriques intérieur et extérieur](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth).
- [Script officiel de conversion vers un nuage de points](https://github.com/DepthAnything/Depth-Anything-V2/blob/main/metric_depth/depth_to_pointcloud.py).
- [Open3D : création d'un nuage depuis une profondeur et des paramètres de caméra](https://www.open3d.org/docs/release/python_api/open3d.geometry.PointCloud.html).
- [OpenCV : projection perspective, paramètres intrinsèques et distorsion](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).
- [COLMAP : photos avec recouvrement, reconstruction multi-vues et fusion](https://colmap.github.io/tutorial.html).

Les exemples utilisent `demo01.jpg` et `demo15.jpg` du dépôt officiel Depth Anything V2. Les photographies personnelles, sorties brutes et nuages privés restent exclus de Git.
