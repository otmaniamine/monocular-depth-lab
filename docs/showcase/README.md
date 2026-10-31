# Visuels pour présenter Monocular Depth Lab

Ces fichiers montrent des résultats réellement calculés, à partir de médias publics. Aucune scène ou géométrie cachée n'a été générée pour améliorer le rendu.

| Fichier | Contenu |
|---|---|
| [01-reconstruction-3d.png](01-reconstruction-3d.png) | Nouvelle photo de logement et nuage de points, 1200 × 800 |
| [reconstruction-3d.gif](reconstruction-3d.gif) | Nuage intérieur seul, sans texte, 960 × 640, boucle de 48 vues |
| [scene-route.jpg](scene-route.jpg) | Photo extérieure réelle, vue depuis la caméra frontale d'une voiture |
| [reconstruction-3d-exterieur.gif](reconstruction-3d-exterieur.gif) | Nuage extérieur seul, sans texte, 960 × 640, boucle de 48 vues |
| [reconstruction-3d-exterieur.png](reconstruction-3d-exterieur.png) | Vue fixe du même nuage extérieur |
| [02-application-industrie.png](02-application-industrie.png) | Photo d'entrepôt et surfaces géométriques à examiner |
| [03-traitement-image.png](03-traitement-image.png) | Photo avant/après flou guidé par la profondeur |
| [04-application-entreprise.png](04-application-entreprise.png) | Prévisualisation d'un volume de meuble dans une pièce |
| [application-video.gif](application-video.gif) | Vidéo routière réelle et annotation des mêmes vues, côte à côte |
| [POST-LINKEDIN.md](POST-LINKEDIN.md) | Proposition de publication courte, sans emojis |

Pour une présentation courte, choisir le GIF de reconstruction puis deux images d'applications. Le GIF vidéo illustre le fonctionnement du prototype hors ligne ; aucune commande n'est envoyée à un véhicule.

## Crédits et portée

- Logement : [Curtis Adams / Pexels](https://www.pexels.com/photo/wooden-floor-inside-the-house-7601090/).
- Entrepôt : [Freek Wolsink / Pexels](https://www.pexels.com/photo/industrial-warehouse-with-stacked-cardboard-boxes-34221998/).
- Vidéo routière : [German Korb / Pexels](https://www.pexels.com/video/dash-cam-footage-in-city-driving-4644521/).

Les médias sources relèvent de la [licence Pexels](https://www.pexels.com/license/). Les auteurs ne cautionnent pas le projet. Voir aussi le [manifeste](../../application/assets/SOURCES.json).

La profondeur provient de Depth Anything V2 Metric Small préentraîné. La reconstruction ne couvre que les surfaces visibles et utilise une focale supposée. La rotation révèle les trous et les déformations : elle ne constitue pas un scan complet de la pièce. Les alertes ne reconnaissent pas les classes d'objets et ne prouvent pas qu'un passage est libre. Les dimensions du meuble virtuel sont illustratives.

## Régénérer les visuels

Depuis la racine du projet, avec les modèles et l'environnement déjà installés :

```powershell
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\application\assets\room.jpg" --model indoor --fov 80 --stride 2 --max-side 960 --output ".\results\3d\showcase"
.\.venv\Scripts\python.exe -m application.run --demo all
.\.venv\Scripts\python.exe -m application.tools.export_showcase
```

La visionneuse interactive complète est créée localement dans `results/3d/showcase/room_indoor.html`. Les données brutes restent dans `results/` et ne sont pas publiées automatiquement. Les paramètres de l'exemple sont conservés dans [reconstruction.json](reconstruction.json).

Pour l'extérieur, la photo est la première image de la vidéo de German Korb créditée ci-dessus. Le modèle extérieur produit 45 031 points avec les paramètres suivants. Le seuil de 35 m est appliqué à la profondeur estimée pour limiter les surfaces lointaines ; le GIF incline aussi la vue pour mieux voir le sol. Aucun texte ni crédit n'est superposé aux deux GIF de reconstruction ; les crédits restent dans ce document.

```powershell
.\.venv\Scripts\python.exe .\reconstruct.py --input ".\application\assets\dashcam.jpg" --model outdoor --fov 75 --stride 2 --max-depth 35 --output ".\results\3d\showcase"
.\.venv\Scripts\python.exe -m application.tools.animate_cloud --cloud ".\results\3d\showcase\room_indoor.npz" --output ".\docs\showcase\reconstruction-3d.gif" --yaw 23
.\.venv\Scripts\python.exe -m application.tools.animate_cloud --cloud ".\results\3d\showcase\dashcam_outdoor.npz" --output ".\docs\showcase\reconstruction-3d-exterieur.gif" --yaw 18 --pitch 22
```
