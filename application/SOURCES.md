# Sources, choix techniques et crédits

Consultation : 20 octobre 2026. Les cas d'usage sont des propositions pour ce projet ; les organisations citées n'ont pas évalué ni approuvé notre code.

## Base technique

- [Depth Anything V2, dépôt officiel](https://github.com/DepthAnything/Depth-Anything-V2) : modèle de profondeur préentraîné, variantes métriques intérieur/extérieur. Les applications utilisent les poids Small déjà installés ; aucun entraînement ajouté.
- [Exemple officiel de projection 3D](https://github.com/DepthAnything/Depth-Anything-V2/blob/main/metric_depth/depth_to_pointcloud.py) et [géométrie de caméra OpenCV](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) : base de la conversion profondeur/pixels vers coordonnées 3D. Notre estimation RANSAC du sol est une heuristique d'application, pas une fonction de conduite autonome fournie par le modèle.
- [Video Depth Anything, dépôt officiel](https://github.com/DepthAnything/Video-Depth-Anything) : travaux spécifiques sur la cohérence temporelle. Ce modèle n'est pas installé ici ; notre traitement image par image avec un compteur d'alerte ne constitue pas un équivalent.

## Utilité pour les entreprises

- [ARCore Depth](https://developers.google.com/ar/develop/depth) documente notamment le masquage des objets virtuels et les effets basés sur la profondeur. Cela motive les démonstrations de gabarit et de flou. ARCore possède une autre méthode d'estimation ; nous n'en reprenons pas la précision annoncée.
- [IKEA Kreativ](https://www.ikea.com/gb/en/customer-service/knowledge/articles/250fg37g-2498-40gg-916c-f27d354683f0.html) illustre l'intérêt commercial de la visualisation d'aménagement. Le gabarit cubique de ce projet est un prototype beaucoup plus limité, sans catalogue, scan complet ni garantie de dimensions.
- [Amazon et l'optimisation des emballages](https://www.aboutamazon.com/news/sustainability/amazon-sustainability-ai-reduce-packaging) donne un exemple de problème industriel où la vision apporte une aide à la décision. Notre démonstration industrielle choisit l'inspection visuelle d'un passage ; elle ne mesure pas des colis pour calculer automatiquement leurs emballages.

Ces sources motivent des usages, pas une preuve de gains commerciaux, de sécurité ou de précision de notre application.

## Médias réels

Les fichiers sont des photos et extraits de vidéos réels, pas des scènes générées par IA. Attribution volontaire, sources et licence listées ci-dessous. Le manifeste [assets/SOURCES.json](assets/SOURCES.json) conserve les liens de téléchargement et les empreintes des fichiers préparés. Les médias sont réencodés sans les métadonnées originales. Les courts extraits vidéo n'ont pas de son.

| Fichier préparé | Auteur | Source |
|---|---|---|
| `street.jpg` | Sami Abdullah | [Circulation urbaine](https://www.pexels.com/photo/cars-in-traffic-on-city-road-16666912/) |
| `room.jpg` | Curtis Adams | [Pièce et parquet](https://www.pexels.com/photo/wooden-floor-inside-the-house-7601090/) |
| `warehouse.jpg` | Erwin Salas | [Allée d'entrepôt](https://www.pexels.com/photo/aisle-of-a-huge-store-24862481/) |
| `boxes.jpg` | Freek Wolsink | [Stockage de cartons](https://www.pexels.com/photo/industrial-warehouse-with-stacked-cardboard-boxes-34221998/) |
| `dashcam.mp4`, `dashcam.jpg` | German Korb | [Caméra frontale en ville](https://www.pexels.com/video/dash-cam-footage-in-city-driving-4644521/) |
| `camera-laterale.mp4`, `camera-laterale.jpg` | Teju | [Vue depuis une fenêtre de voiture](https://www.pexels.com/video/a-person-is-driving-down-the-road-with-a-car-19713833/) |

[Licence Pexels](https://www.pexels.com/license/) pour les médias sources. Ils restent soumis à cette licence et aux droits applicables, indépendamment de la licence du code. Les photographes et Pexels ne cautionnent pas le projet. Les annotations, cartes de profondeur, volumes virtuels et flous sont nos transformations de ces médias.
